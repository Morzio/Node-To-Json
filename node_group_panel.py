import bpy
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ExportHelper, ImportHelper
from pathlib import Path
from time import perf_counter
import node_to_json as n2j


def node_group_selection(self, context):
    return [("GeometryNodeTree", "Geometry Nodes", "Show Geometry Node Groups"), ("ShaderNodeTree", "Shader Nodes", "Show Shader Node Groups"), ("CompositorNodeTree", "Compositor Nodes", "Show Compositor Node Groups"), ("TextureNodeTree", "Texture Nodes", "Show Texture Node Groups")]


def indent_selection(self, context):
    return [("None", "None", "Use no indent"), ("0", "0", "Indent with no space"), ("2", "2", "Indent with 2 spaces"), ("4", "4", "Indent with 4 spaces")]


def update_node_group_selection(self, context):
    bpy.ops.scene.add_node_group_item()


def get_populate_node_groups(context):
    scene = context.scene
    return n2j.get_node_groups_by_type(scene.ng_selection_type)


def populate_node_groups(context):
    scene = context.scene
    groups = get_populate_node_groups(context)
    scene.node_group_items.clear()
    for group in groups:
        new_item = scene.node_group_items.add()
        new_item.name = group.name


class NodeGroupItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Item Name", default="")


class NG_UL_node_group_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon=icon)


class NODES_PT_ng_panel(bpy.types.Panel):
    """Node To Json graphical user interface"""
    bl_label = "Node To Json"
    bl_idname = "NODES_PT_ng_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Node To Json"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        layout.label(text="Node Group Panel")

        layout.template_list(
            "NG_UL_node_group_list", 
            "", 
            scn, 
            "node_group_items", 
            scn, 
            "ng_items_index"
        )

        interface_box = layout.box()
        export_box = interface_box.box()
        mode_row = export_box.row()
        mode_row.prop(scn, "ng_selection_type", text="Mode")
        mode_row.operator(ExportSerializedNodeGroup.bl_idname, text="", icon='DISK_DRIVE', emboss=True)
        indent_row = export_box.row()
        indent_row.prop(scn, "ng_indent_type", text="Indent")
        indent_row.operator(ImportNodeGroupData.bl_idname, text="", icon='FILE_FOLDER', emboss=True)


class SCENE_OT_add_node_group_item(bpy.types.Operator):
    bl_idname = "scene.add_node_group_item"
    bl_label = "Populate Node Groups"

    def execute(self, context):
        populate_node_groups(context)
        return {'FINISHED'}


class NodeGroupDetector(bpy.types.Operator):
    """Listener to detect when a new Node Group is added to the scene"""
    bl_idname = "scene.detect_new_node_group"
    bl_label = "Detect New Node Group"

    _timer = None
    _prev_group_names = set()

    def modal(self, context, event):
        if event.type == 'TIMER':
            current_names = {ng.name for ng in bpy.data.node_groups}
            if current_names != self._prev_group_names:
                bpy.ops.scene.add_node_group_item()
                self._prev_group_names = current_names
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        self._prev_group_names = {ng.name for ng in bpy.data.node_groups}
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)


class ExportSerializedNodeGroup(bpy.types.Operator, ExportHelper):
    """Export Serialized Node Group Data """
    bl_idname = "scene.serialize_node_group"
    bl_label = "Export Node Group"

    use_filter_folder = True

    filename_ext = ""

    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  
    )

    def execute(self, context):
        t_start = perf_counter()
        # Get available Node Groups
        groups = list(get_populate_node_groups(context))
        if len(groups) == 0:
            self.report({'ERROR'}, "No Node Groups Available!")
            return {'CANCELLED'}
        # Get selected Node Group
        group = groups[context.scene.ng_items_index]
        # Get Node Group getter function
        get_func = n2j.ng_getter_funcs.get(group.bl_idname)
        data = get_func(group)
        # Determine if the filepath is a directory. If not, use the parent directory
        fp = Path(self.filepath)
        if not fp.is_dir():
            fp = fp.parent
        _file = str(fp.joinpath(f"{group.name}.json"))
        # Get the indent to use for the JSON file
        _indent = (None if context.scene.ng_indent_type == 'None' else int(context.scene.ng_indent_type))
        # Save the data dict to JSON file
        n2j.dict_to_json(_file, data, indent=_indent)
        t_end = perf_counter()
        self.report({'INFO'}, f"[{(t_end - t_start):.4f} Sec] Successfully saved {group.name} to {_file}!")
        return {'FINISHED'}


class ImportNodeGroupData(bpy.types.Operator, ImportHelper):
    """Import Node Group JSON Data"""
    bl_idname = "scene.json_node_group" 
    bl_label = "Import Node Group"

    filename_ext = ".json"

    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255, 
    )

    def execute(self, context):
        t_start = perf_counter()
        # Load JSON file data
        data = n2j.json_to_dict(self.filepath)
        # Get the setter function
        try:
            ng_type = n2j.get_node_group_data_type(data)
        except TypeError as t:
            try:
                ng_type = n2j.get_node_group_data_type(data["node_groups"])
            except:
                self.report({'ERROR'}, ("Can not find Node Group Type!", t))
        if not ng_type:
            self.report({'ERROR'}, "Can not find Node Group Type!")
            return {'CANCELLED'}
        set_func = n2j.ng_setter_funcs.get(ng_type)
        # Build the Node Group from the data
        node_group = set_func(data)
        t_end = perf_counter()
        populate_node_groups(context)
        self.report({'INFO'}, f"[{(t_end - t_start):.4f} Sec] Successfully created {node_group.name}!")
        return {'FINISHED'}




classes = [
    NodeGroupItem, 
    NG_UL_node_group_list, 
    NODES_PT_ng_panel, 
    SCENE_OT_add_node_group_item, 
    NodeGroupDetector, 
    ExportSerializedNodeGroup, 
    ImportNodeGroupData, 
]


def register():
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.node_group_items = bpy.props.CollectionProperty(type=NodeGroupItem)
    bpy.types.Scene.ng_items_index = bpy.props.IntProperty(default=0)
    bpy.types.Scene.ng_selection_type = bpy.props.EnumProperty(
        name = "Node Group Type",
        description = "Select a node group type.",
        items = node_group_selection,
        update=update_node_group_selection,
    )
    bpy.types.Scene.ng_indent_type = bpy.props.EnumProperty(
        name = "Indent Type",
        description = "Select a json indent type.",
        items = indent_selection,
    )


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.ng_indent_type
    del bpy.types.Scene.ng_selection_type
    del bpy.types.Scene.ng_items_index
    del bpy.types.Scene.node_group_items

if __name__ == "__main__":
    register()






