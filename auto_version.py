
import bpy
import os
import re
import blf
from bpy.app.handlers import persistent

# ------------------------------------------------------------
# Globals
# ------------------------------------------------------------

_draw_handler = None
_overlay_visible = True
_current_version_text = ""

# ------------------------------------------------------------
# Task Rules
# ------------------------------------------------------------

TASK_TYPES_WITH_UNDERSCORE = [
    "layout", "blocking", "polish", "lighting", "render"
]

TASK_TYPES_NO_UNDERSCORE = [
    "modeling", "shading", "rigging", "lookdev"
]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def has_version_in_name(base_name):
    return re.search(r"_v\d{2}$", base_name) is not None


def get_task_types(base_name):
    return TASK_TYPES_WITH_UNDERSCORE if "_" in base_name else TASK_TYPES_NO_UNDERSCORE


def get_version_folder():
    if not bpy.data.filepath:
        return None
    directory = os.path.dirname(bpy.data.filepath)
    return os.path.join(directory, ".version")


def get_latest_file_by_time(version_folder):
    if not version_folder or not os.path.exists(version_folder):
        return None

    files = [
        os.path.join(version_folder, f)
        for f in os.listdir(version_folder)
        if f.endswith(".blend")
    ]

    if not files:
        return None

    latest = max(files, key=os.path.getmtime)
    return os.path.basename(latest)


def get_latest_version_number(version_folder, base_name, task_type):
    if not version_folder or not os.path.exists(version_folder):
        return 0

    pattern = re.compile(
        rf"{re.escape(base_name)}_{re.escape(task_type)}_v(\d{{2}})\.blend"
    )

    versions = []

    for f in os.listdir(version_folder):
        m = pattern.match(f)
        if m:
            versions.append(int(m.group(1)))

    return max(versions) if versions else 0


def get_simple_version_number(version_folder, base_name):
    if not version_folder or not os.path.exists(version_folder):
        return 0

    pattern = re.compile(
        rf"{re.escape(base_name)}_v(\d{{2}})\.blend"
    )

    versions = []

    for f in os.listdir(version_folder):
        m = pattern.match(f)
        if m:
            versions.append(int(m.group(1)))

    return max(versions) if versions else 0
    

# 🔥 FIXED TASK TYPE PARSER
def get_task_type_from_filename(filename):
    """
    Extract task type safely from filename like:
    shot010_001_lighting_v03.blend
    → lighting
    """

    name = os.path.splitext(filename)[0]

    base = re.sub(r"_v\d{2}$", "", name)
    parts = base.split("_")

    if len(parts) >= 2:
        return parts[-1].lower()

    return None


def get_latest_task_type():
    version_folder = get_version_folder()
    latest = get_latest_file_by_time(version_folder)

    if not latest:
        return None

    return get_task_type_from_filename(latest)


def update_current_version_text():
    global _current_version_text

    version_folder = get_version_folder()
    latest = get_latest_file_by_time(version_folder)

    if latest:
        _current_version_text = f"Current Version: {latest}"
    else:
        _current_version_text = ""


# ------------------------------------------------------------
# Viewport Draw
# ------------------------------------------------------------

def draw_callback_px(self, context):
    if not _overlay_visible:
        return

    if not _current_version_text:
        return

    font_id = 0
    blf.position(font_id, 20, 20, 0)
    blf.size(font_id, 12)
    blf.draw(font_id, _current_version_text)


# ------------------------------------------------------------
# Toggle Overlay Operator (Ctrl + T)
# ------------------------------------------------------------

class WM_OT_toggle_version_overlay(bpy.types.Operator):
    bl_idname = "wm.toggle_version_overlay"
    bl_label = "Toggle Version Overlay"

    def execute(self, context):
        global _overlay_visible
        _overlay_visible = not _overlay_visible

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        return {'FINISHED'}


# ------------------------------------------------------------
# Save Operator (Ctrl + S)
# ------------------------------------------------------------

def build_enum_items(self, context):
    if not bpy.data.filepath:
        return []

    filename = os.path.basename(bpy.data.filepath)
    base_name, _ = os.path.splitext(filename)

    tasks = get_task_types(base_name)
    return [(t, t.capitalize(), "") for t in tasks]


class WM_OT_save_with_version(bpy.types.Operator):
    bl_idname = "wm.save_with_task_version"
    bl_label = "Save With Version"

    task_type: bpy.props.EnumProperty(
        name="Task Type",
        items=build_enum_items
    )

    def invoke(self, context, event):

        if not bpy.data.filepath:
            self.report({'ERROR'}, "Please save file first.")
            return {'CANCELLED'}

        filename = os.path.basename(bpy.data.filepath)
        base_name, _ = os.path.splitext(filename)

        # Nếu file đã có version → save bình thường
        if has_version_in_name(base_name):
            bpy.ops.wm.save_mainfile()
            return {'CANCELLED'}

        # 🔥 AUTO DEFAULT TASK TYPE
        latest_task = get_latest_task_type()
        valid_items = [item[0] for item in build_enum_items(self, context)]

        if latest_task and latest_task in valid_items:
            self.task_type = latest_task


        return context.window_manager.invoke_props_dialog(self)

#    def draw(self, context):
#        if "_" in base_name:
#            self.layout.label(text=r"{latest_version}")
#        else: 
#            self.layout.prop(self, "task_type")

    def draw(self, context):
        layout = self.layout
        filename = os.path.basename(bpy.data.filepath)
        base_name, _ = os.path.splitext(filename)
        version_folder = get_version_folder()

        # Lấy tên file mới nhất hiện có trong folder .version
        latest_file = get_latest_file_by_time(version_folder)
        
        if "_" in base_name:
            box = layout.box()
            box.label(text="Latest Version Found:")
            
            if latest_file:
                # Hiển thị tên file phiên bản gần nhất
                box.label(text=latest_file, icon='CHECKMARK')
            else:
                # Trường hợp thư mục .version trống hoặc chưa có file
                box.label(text="No previous versions found.", icon='INFO')
            
        else:
            # Nếu không, hiển thị menu chọn Task
            layout.prop(self, "task_type", text="Task Type")


    def execute(self, context):

        directory = os.path.dirname(bpy.data.filepath)
        filename = os.path.basename(bpy.data.filepath)
        base_name, _ = os.path.splitext(filename)

        version_folder = os.path.join(directory, ".version")
        os.makedirs(version_folder, exist_ok=True)

        # 🔹 Luôn save file gốc trước
        bpy.ops.wm.save_mainfile()

        if "_" in base_name:
            # Trường hợp file có gạch dưới: Tên file = base_name_vXX.blend
            latest_version = get_simple_version_number(version_folder, base_name)
            new_version = latest_version + 1
            new_filename = f"{base_name}_v{new_version:02d}.blend"
        else:
            # Trường hợp file không có gạch dưới: Tên file = base_name_task_vXX.blend
            latest_version = get_latest_version_number(
                version_folder, 
                base_name, 
                self.task_type
            )
            new_version = latest_version + 1
            new_filename = f"{base_name}_{self.task_type}_v{new_version:02d}.blend"
            
        new_path = os.path.join(version_folder, new_filename)

        bpy.ops.wm.save_as_mainfile(filepath=new_path, copy=True)

        update_current_version_text()

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        self.report({'INFO'}, f"Saved: {new_filename}")
        return {'FINISHED'}


# ------------------------------------------------------------
# Handlers
# ------------------------------------------------------------

@persistent
def load_handler(dummy):
    update_current_version_text()


# ------------------------------------------------------------
# Register
# ------------------------------------------------------------

addon_keymaps = []

def register():
    global _draw_handler

    bpy.utils.register_class(WM_OT_save_with_version)
    bpy.utils.register_class(WM_OT_toggle_version_overlay)

    bpy.app.handlers.load_post.append(load_handler)

    _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
        draw_callback_px,
        (None, None),
        'WINDOW',
        'POST_PIXEL'
    )

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = kc.keymaps.new(name='Window', space_type='EMPTY')

        # Ctrl + S
        kmi = km.keymap_items.new(
            WM_OT_save_with_version.bl_idname,
            type='S',
            value='PRESS',
            ctrl=True,
            alt=True
        )
        addon_keymaps.append((km, kmi))

        # Ctrl + T
        kmi_toggle = km.keymap_items.new(
            WM_OT_toggle_version_overlay.bl_idname,
            type='T',
            value='PRESS',
            ctrl=True
        )
        addon_keymaps.append((km, kmi_toggle))


def unregister():
    global _draw_handler

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    if _draw_handler:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None

    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)

    bpy.utils.unregister_class(WM_OT_save_with_version)
    bpy.utils.unregister_class(WM_OT_toggle_version_overlay)


if __name__ == "__main__":
    register()