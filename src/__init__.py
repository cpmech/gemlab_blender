import blf
import bpy
from bpy_extras import view3d_utils


bl_info = {
    "name": "Gemlab",
    "author": "Dorival Pedroso",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "description": "Tool to write Gemlab (and Tritet) input data files",
    "category": "3D View",
}


def draw_callback_px(self, context):
    # check if we need to draw
    wm = context.window_manager
    if not getattr(wm, "do_show_tags", False):
        return

    # get the object
    ob = context.object
    if not ob:
        return
    if not ob.type == "MESH":
        return

    # write status message
    font_id = 0
    blf.position(font_id, 45, 45, 0)
    blf.size(font_id, 15)
    blf.draw(font_id, "displaying tags")

    # get the region and region_3d
    # Note, according to https://docs.blender.org/api/current/bpy_extras.view3d_utils.html:
    #    r3d is a "3D region data, typically bpy.context.space_data.region_3d"
    #    r3d is a RegionView3D(bpy_struct), see https://docs.blender.org/api/current/bpy.types.RegionView3D.html
    reg = bpy.context.region
    r3d = bpy.context.space_data.region_3d

    # get the scene
    sc = context.scene

    # transformation matrix (local co => global co)
    T = ob.matrix_world.copy()

    # vertex tags
    if len(ob.vtags) > 0 and sc.gemlab_show_vtag:
        blf.size(font_id, sc.gemlab_vert_font)
        r, g, b = sc.gemlab_vert_color
        blf.color(font_id, r, g, b, 1.0)
        for v in ob.vtags.values():
            if v.tag >= 0:
                continue
            pm = ob.data.vertices[v.idx].co
            co = view3d_utils.location_3d_to_region_2d(reg, r3d, T @ pm)
            if co:
                blf.position(font_id, co[0], co[1], 0)
                blf.draw(font_id, "%d" % v.tag)

    # edge tags
    if len(ob.etags) > 0 and sc.gemlab_show_etag:
        blf.size(font_id, sc.gemlab_edge_font)
        r, g, b = sc.gemlab_edge_color
        blf.color(font_id, r, g, b, 1.0)
        for v in ob.etags.values():
            if v.tag >= 0:
                continue
            pa = ob.data.vertices[v.v0].co
            pb = ob.data.vertices[v.v1].co
            pm = (pa + pb) / 2.0
            co = view3d_utils.location_3d_to_region_2d(reg, r3d, T @ pm)
            if co:
                blf.position(font_id, co[0], co[1], 0)
                blf.draw(font_id, "%d" % v.tag)

    # cell tags
    if len(ob.ctags) > 0 and sc.gemlab_show_ctag:
        blf.size(font_id, sc.gemlab_cell_font)
        r, g, b = sc.gemlab_cell_color
        blf.color(font_id, r, g, b, 1.0)
        for v in ob.ctags.values():
            if v.tag >= 0:
                continue
            c = ob.data.polygons[v.idx]
            pm = ob.data.vertices[c.vertices[0]].co.copy()
            for k in range(1, len(c.vertices)):
                pm += ob.data.vertices[c.vertices[k]].co
            pm /= float(len(c.vertices))
            co = view3d_utils.location_3d_to_region_2d(reg, r3d, T @ pm)
            if co:
                blf.position(font_id, co[0], co[1], 0)
                blf.draw(font_id, "%d" % v.tag)


class GemlabDisplayTags(bpy.types.Operator):
    bl_idname = "view3d.show_tags"
    bl_label = "Show Tags"
    bl_description = "Display tags on top of mesh"
    _handle = None  # (static/global) will be assigned by invoke

    @staticmethod
    def handle_remove(context):
        if GemlabDisplayTags._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(GemlabDisplayTags._handle, "WINDOW")
        GemlabDisplayTags._handle = None

    def modal(self, context, event):
        # stop script
        if not getattr(context.window_manager, "do_show_tags", False):
            GemlabDisplayTags.handle_remove(context)
            return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def cancel(self, context):
        if getattr(context.window_manager, "do_show_tags", False):
            GemlabDisplayTags.handle_remove(context)
            setattr(context.window_manager, "do_show_tags", False)
        return {"CANCELLED"}

    def invoke(self, context, event):
        if context.area.type == "VIEW_3D":
            # operator is called for the first time, start everything
            if not getattr(context.window_manager, "do_show_tags", False):
                setattr(context.window_manager, "do_show_tags", True)
                GemlabDisplayTags._handle = bpy.types.SpaceView3D.draw_handler_add(
                    draw_callback_px, (self, context), "WINDOW", "POST_PIXEL"
                )
                context.area.tag_redraw()  # refresh
                return {"RUNNING_MODAL"}
            # operator is called again, stop displaying
            else:
                setattr(context.window_manager, "do_show_tags", False)
                context.area.tag_redraw()  # refresh
                return {"CANCELLED"}
        else:
            self.report({"WARNING"}, "View3D not found, can't run operator")
            return {"CANCELLED"}

    @staticmethod
    def unregister():
        if bpy.context:
            GemlabDisplayTags.handle_remove(bpy.context)


class SetVertexTag(bpy.types.Operator):
    bl_idname = "gemlab.set_vert_tag"
    bl_label = "Set vertex tag"
    bl_description = "Set vertex tag (for selected vertices)"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and "EDIT" in context.object.mode

    def execute(self, context):
        bpy.ops.object.editmode_toggle()
        sc = context.scene
        ob = context.object
        vids = [v.idx for v in ob.vtags.values()]
        for v in ob.data.vertices:
            if v.select:  # vertex is selected
                if v.index in vids:  # update
                    ob.vtags[vids.index(v.index)].tag = sc.gemlab_default_vert_tag
                else:
                    new = ob.vtags.add()
                    new.tag = sc.gemlab_default_vert_tag
                    new.idx = v.index
        bpy.ops.object.editmode_toggle()
        return {"FINISHED"}


class SetEdgeTag(bpy.types.Operator):
    bl_idname = "gemlab.set_edge_tag"
    bl_label = "Set edge tag"
    bl_description = "Set edge tag (for selected edges)"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and "EDIT" in context.object.mode

    def execute(self, context):
        bpy.ops.object.editmode_toggle()
        sc = context.scene
        ob = context.object
        ekeys = [(v.v0, v.v1) for v in ob.etags.values()]
        for e in ob.data.edges:
            if e.select:  # edge is selected
                if e.key in ekeys:  # update
                    ob.etags[ekeys.index(e.key)].tag = sc.gemlab_default_edge_tag
                else:
                    new = ob.etags.add()
                    new.tag = sc.gemlab_default_edge_tag
                    new.v0 = e.key[0]
                    new.v1 = e.key[1]
        bpy.ops.object.editmode_toggle()
        return {"FINISHED"}


class SetCellTag(bpy.types.Operator):
    bl_idname = "gemlab.set_cell_tag"
    bl_label = "Set cell tag"
    bl_description = "Set cell tag (for selected faces)"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH" and "EDIT" in context.object.mode

    def execute(self, context):
        bpy.ops.object.editmode_toggle()
        sc = context.scene
        ob = context.object
        cids = [v.idx for v in ob.ctags.values()]
        for p in ob.data.polygons:
            if p.select:  # polygon is selected
                if p.index in cids:  # update
                    ob.ctags[cids.index(p.index)].tag = sc.gemlab_default_cell_tag
                else:
                    new = ob.ctags.add()
                    new.tag = sc.gemlab_default_cell_tag
                    new.idx = p.index
        bpy.ops.object.editmode_toggle()
        return {"FINISHED"}


def write_2d_msh_file(operator_instance, filepath, context, tol=0.0001):
    # get the object
    obj = context.object
    if obj is None or obj.type != "MESH":
        operator_instance.report({"ERROR"}, "No mesh object selected")
        return {"CANCELLED"}

    # get the mesh data
    mesh = obj.data
    if mesh is None:
        operator_instance.report({"ERROR"}, "No mesh data found")
        return {"CANCELLED"}

    # check if any z-coordinate is non-zero
    operator_instance.report({"INFO"}, "Checking z-coordinates of vertices...")
    for i, v in enumerate(mesh.vertices):
        co = obj.matrix_world @ v.co
        if abs(co[2]) > 0.0:
            operator_instance.report({"ERROR"}, f"Vertex {i} has non-zero z-coordinate ({co[2]})")
            return {"CANCELLED"}

    # get ides and tags (markers)
    vids = [v.idx for v in obj.vtags.values()]
    ekeys = [(v.v0, v.v1) for v in obj.etags.values()]
    cids = [v.idx for v in obj.ctags.values()]

    # number of vertices and cells
    npoint = len(mesh.vertices)  # total number of vertices
    ncell = len(obj.data.polygons)  # total number of cells
    nmarked_edge = len(obj.etags)

    # initialize buffer
    operator_instance.report({"INFO"}, "Writing to buffer...")
    buf = "# header\n"
    buf += "# ndim npoint ncell nmarked_edge nmarked_face\n"
    buf += f"2 {npoint} {ncell} {nmarked_edge} 0\n\n"

    # points (vertices)
    buf += "# points\n"
    buf += "# id marker x y\n"
    for i, v in enumerate(mesh.vertices):
        co = obj.matrix_world @ v.co
        marker = obj.vtags[vids.index(v.index)].tag if (v.index in vids) else 0
        buf += f"{i} {marker} {co[0]} {co[1]}\n"

    # cells
    buf += "\n# cells\n"
    buf += "# id attribute kind points\n"
    for i, p in enumerate(obj.data.polygons):
        # check normal vector
        n = p.normal
        if abs(n[0]) > tol or abs(n[1]) > tol:
            operator_instance.report({"ERROR"}, "Face has normal non-parallel to z")
            return {"CANCELLED"}
        if n[2] < tol:
            operator_instance.report({"ERROR"}, "Face has wrong normal; vertices must be counter-clockwise")
            return {"CANCELLED"}

        # number of nodes (vertices) in the polygon/element
        nnode = len(p.vertices)
        if not (nnode == 3 or nnode == 4):
            operator_instance.report({"ERROR"}, "Only 3-node and 4-node elements are supported")
            return {"CANCELLED"}

        # detect geometry kind (it must be lin3 or qua4)
        kind = "lin3" if nnode == 3 else "qua4"

        # cell attribute (marker/tag)
        attribute = obj.ctags[cids.index(p.index)].tag if (p.index in cids) else 0
        buf += f"{i} {attribute} {kind}"
        for i in range(nnode):
            buf += f" {obj.data.vertices[p.vertices[i]].index}"

        # next line
        buf += "\n"

    # marked edges
    if nmarked_edge > 0:
        buf += "\n# marked edges\n"
        if nnode == 3:
            buf += "# marker p1 p2 p3\n"
        else:
            buf += "# marker p1 p2 p3 p4\n"
        for edge_key in ekeys:
            v0, v1 = edge_key
            marker = obj.etags[ekeys.index(edge_key)].tag
            buf += f"{marker} {v0} {v1}\n"

    # write buffer to file
    f = open(filepath, "w")
    f.write(buf)
    f.close()

    # success
    operator_instance.report({"INFO"}, "Successfully wrote to buffer.")
    return {"FINISHED"}


class GemlabExporter(bpy.types.Operator):
    bl_idname = "gemlab.export_mesh"
    bl_label = "Write 2D msh file"
    bl_description = "Write 2D msh file. This only works if all z-coordinates are zero."

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH",
    )
    check_existing: bpy.props.BoolProperty(
        name="Check Existing",
        description="Check and warn on overwriting existing files",
        default=True,
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "MESH"

    def execute(self, context):
        bpy.ops.object.editmode_toggle()
        status = write_2d_msh_file(self, self.filepath, context)
        bpy.ops.object.editmode_toggle()
        return status

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".msh")
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ObjectVertTag(bpy.types.PropertyGroup):
    tag: bpy.props.IntProperty()
    idx: bpy.props.IntProperty()


class ObjectEdgeTag(bpy.types.PropertyGroup):
    tag: bpy.props.IntProperty()
    v0: bpy.props.IntProperty()
    v1: bpy.props.IntProperty()


class ObjectCellTag(bpy.types.PropertyGroup):
    tag: bpy.props.IntProperty()
    idx: bpy.props.IntProperty()


def init_properties():
    # object data
    bpy.types.Object.vtags = bpy.props.CollectionProperty(type=ObjectVertTag)
    bpy.types.Object.etags = bpy.props.CollectionProperty(type=ObjectEdgeTag)
    bpy.types.Object.ctags = bpy.props.CollectionProperty(type=ObjectCellTag)

    # scene data
    scene = bpy.types.Scene
    scene.gemlab_default_edge_tag = bpy.props.IntProperty(
        name="E", description="Default Edge Tag", default=-10, min=-99, max=0
    )

    scene.gemlab_default_vert_tag = bpy.props.IntProperty(
        name="V", description="Default Vertex Tag", default=-100, min=-1000, max=0
    )

    scene.gemlab_default_cell_tag = bpy.props.IntProperty(
        name="C", description="Default Cell Tag", default=-1, min=-99, max=0
    )

    # show tags
    scene.gemlab_show_etag = bpy.props.BoolProperty(name="Edge", description="Display Edge Tags", default=True)

    scene.gemlab_show_vtag = bpy.props.BoolProperty(name="Vertex", description="Display Vertex Tags", default=True)

    scene.gemlab_show_ctag = bpy.props.BoolProperty(name="Cell", description="Display Cell Tags", default=True)

    # font sizes
    scene.gemlab_vert_font = bpy.props.IntProperty(name="V", description="Vertex font size", default=12, min=6, max=100)

    scene.gemlab_edge_font = bpy.props.IntProperty(name="E", description="Edge font size", default=12, min=6, max=100)

    scene.gemlab_cell_font = bpy.props.IntProperty(name="C", description="Edge font size", default=20, min=6, max=100)

    # font colors
    scene.gemlab_vert_color = bpy.props.FloatVectorProperty(
        name="V",
        description="Vertex color",
        default=(1.0, 0.805, 0.587),
        min=0,
        max=1,
        subtype="COLOR",
    )

    scene.gemlab_edge_color = bpy.props.FloatVectorProperty(
        name="E",
        description="Edge color",
        default=(0.934, 0.764, 1.0),
        min=0,
        max=1,
        subtype="COLOR",
    )

    scene.gemlab_cell_color = bpy.props.FloatVectorProperty(
        name="C",
        description="Cell color",
        default=(0.504, 0.786, 1.0),
        min=0,
        max=1,
        subtype="COLOR",
    )

    # do_show_tags is initially always False and it is in the window manager, not the scene
    wm = bpy.types.WindowManager
    wm.do_show_tags = bpy.props.BoolProperty(default=False)


class VIEW3D_PT_GemlabPanel(bpy.types.Panel):
    bl_label = "Gemlab and Tritet Input File Writer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gemlab"
    bl_idname = "VIEW3D_PT_GemlabPanel"

    def draw(self, context):
        sc = context.scene
        wm = context.window_manager
        lo = self.layout

        lo.label(text="Set tags:")
        c = lo.column(align=True)
        r = c.row(align=True)
        r.prop(sc, "gemlab_default_vert_tag")
        r.operator("gemlab.set_vert_tag")
        r = c.row(align=True)
        r.prop(sc, "gemlab_default_edge_tag")
        r.operator("gemlab.set_edge_tag")
        r = c.row(align=True)
        r.prop(sc, "gemlab_default_cell_tag")
        r.operator("gemlab.set_cell_tag")

        lo.label(text="Show/hide:")
        c = lo.column(align=True)
        r = c.row(align=True)
        r.prop(sc, "gemlab_show_vtag")
        r.prop(sc, "gemlab_show_etag")
        r.prop(sc, "gemlab_show_ctag")
        if not getattr(wm, "do_show_tags", False):
            lo.operator("view3d.show_tags", text="Start display", icon="PLAY")
        else:
            lo.operator("view3d.show_tags", text="Stop display", icon="PAUSE")

        lo.label(text="Font size and colors:")
        c = lo.column(align=True)
        r = c.row(align=True)
        r.prop(sc, "gemlab_vert_font")
        r.prop(sc, "gemlab_vert_color", text="")
        r = c.row(align=True)
        r.prop(sc, "gemlab_edge_font")
        r.prop(sc, "gemlab_edge_color", text="")
        r = c.row(align=True)
        r.prop(sc, "gemlab_cell_font")
        r.prop(sc, "gemlab_cell_color", text="")

        lo.label(text="Export data:")
        lo.operator("gemlab.export_mesh", text="Write 2D msh file")


# Classes to register
classes = (
    ObjectVertTag,
    ObjectEdgeTag,
    ObjectCellTag,
    GemlabDisplayTags,
    SetVertexTag,
    SetEdgeTag,
    SetCellTag,
    GemlabExporter,
    VIEW3D_PT_GemlabPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    init_properties()


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Clean up properties
    del bpy.types.Object.vtags
    del bpy.types.Object.etags
    del bpy.types.Object.ctags
    del bpy.types.Scene.gemlab_default_edge_tag
    del bpy.types.Scene.gemlab_default_vert_tag
    del bpy.types.Scene.gemlab_default_cell_tag
    del bpy.types.Scene.gemlab_show_etag
    del bpy.types.Scene.gemlab_show_vtag
    del bpy.types.Scene.gemlab_show_ctag
    del bpy.types.Scene.gemlab_vert_font
    del bpy.types.Scene.gemlab_edge_font
    del bpy.types.Scene.gemlab_cell_font
    del bpy.types.Scene.gemlab_vert_color
    del bpy.types.Scene.gemlab_edge_color
    del bpy.types.Scene.gemlab_cell_color
    del bpy.types.WindowManager.do_show_tags


if __name__ == "__main__":
    register()
