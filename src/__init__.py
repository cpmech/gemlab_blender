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
    wm = context.window_manager
    sc = context.scene
    if not getattr(wm, "do_show_tags", False):
        return
    ob = context.object
    if not ob:
        return
    if not ob.type == "MESH":
        return

    # status
    font_id = 0
    blf.position(font_id, 45, 45, 0)
    blf.size(font_id, 15)
    blf.draw(font_id, "displaying tags")

    # region
    reg = bpy.context.region
    r3d = bpy.context.space_data.region_3d

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
    last_activity = "NONE"
    _handle = None
    _timer = None

    def handle_add(self, context):
        GemlabDisplayTags._handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_px, (self, context), "WINDOW", "POST_PIXEL"
        )
        GemlabDisplayTags._timer = context.window_manager.event_timer_add(
            time_step=0.075, window=context.window
        )

    @staticmethod
    def handle_remove(context):
        if GemlabDisplayTags._handle is not None:
            context.window_manager.event_timer_remove(GemlabDisplayTags._timer)
            bpy.types.SpaceView3D.draw_handler_remove(
                GemlabDisplayTags._handle, "WINDOW"
            )
        GemlabDisplayTags._handle = None
        GemlabDisplayTags._timer = None

    def modal(self, context, event):  # type: ignore
        # redraw
        # if context.area:
        # context.area.tag_redraw()
        # stop script
        if not getattr(context.window_manager, "do_show_tags", False):
            GemlabDisplayTags.handle_remove(context)
            return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def cancel(self, context):  # type: ignore
        if getattr(context.window_manager, "do_show_tags", False):
            GemlabDisplayTags.handle_remove(context)
            setattr(context.window_manager, "do_show_tags", False)
        return {"CANCELLED"}

    def invoke(self, context, event):  # type: ignore
        if context.area.type == "VIEW_3D":
            # operator is called for the first time, start everything
            if not getattr(context.window_manager, "do_show_tags", False):
                setattr(context.window_manager, "do_show_tags", True)
                GemlabDisplayTags.handle_add(self, context)
                return {"RUNNING_MODAL"}
            # operator is called again, stop displaying
            else:
                setattr(context.window_manager, "do_show_tags", False)
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
        return (
            context.object
            and (context.object.type == "MESH")
            and ("EDIT" in context.object.mode)
        )

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
        return (
            context.object
            and (context.object.type == "MESH")
            and ("EDIT" in context.object.mode)
        )

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
        return (
            context.object
            and (context.object.type == "MESH")
            and ("EDIT" in context.object.mode)
        )

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


def write_mesh_to_file(
    filepath, context, drawmesh=False, ids=False, tags=True, tol=0.0001, flatten=False
):
    ob = context.object
    me = ob.data
    T = ob.matrix_world.copy()
    vids = [v.idx for v in ob.vtags.values()]
    ekeys = [(v.v0, v.v1) for v in ob.etags.values()]
    cids = [v.idx for v in ob.ctags.values()]
    errors = ""
    # header
    out = ""
    # vertices
    out += "V=[\n"
    for k, v in enumerate(me.vertices):
        if flatten and abs(v.co[2]) > 0.0:
            v.co[2] = 0.0
        co = T @ v.co
        tg = ob.vtags[vids.index(v.index)].tag if (v.index in vids) else 0
        out += "  [%d, %d, %.8f, %.8f]" % (k, tg, co[0], co[1])
        if k < len(me.vertices) - 1:
            out += ","
        out += "\n"
    # cells
    nc = len(ob.data.polygons)  # number of cells
    out += "]\nC=[\n"
    for i, p in enumerate(ob.data.polygons):
        tg = ob.ctags[cids.index(p.index)].tag if (p.index in cids) else 0
        n = p.normal
        err = ""
        if abs(n[0]) > tol or abs(n[1]) > tol:
            err += "Face has normal non-parallel to z"
        if n[2] < tol:
            err += "Face has wrong normal; vertices must be counter-clockwise"
        out += "  [%d, %d, [" % (i, tg)
        et = {}  # edge tags
        nv = len(p.vertices)  # number of vertices
        for k in range(nv):
            v0, v1 = (
                ob.data.vertices[p.vertices[k]].index,
                ob.data.vertices[p.vertices[(k + 1) % nv]].index,
            )
            out += "%d" % v0
            if k < nv - 1:
                out += ","
            else:
                out += "]"
            ek = (v0, v1) if v0 < v1 else (v1, v0)  # edge key
            if ek in ekeys:
                if ob.etags[ekeys.index(ek)].tag >= 0:
                    continue
                et[k] = ob.etags[ekeys.index(ek)].tag
        if len(et) > 0:
            out += ", {"
        k = 0
        for idx, tag in et.items():
            out += "%d:%d" % (idx, tag)
            if k < len(et) - 1:
                out += ", "
            else:
                out += "}"
            k += 1
        if i < nc - 1:
            out += "],"
        else:
            out += "]"
        if err != "":
            out += "# " + err
            errors = err
        out += "\n"
    out += "]\n"
    # footer
    if drawmesh:
        out += "d = DrawMesh(V, C)\n"
        out += "d.draw(with_ids=%s, with_tags=%s)\n" % (str(ids), str(tags))
        out += "d.show()\n"
    # write to file
    f = open(filepath, "w")
    f.write(out)
    f.close()
    return errors


class GemlabExporter(bpy.types.Operator):
    bl_idname = "gemlab.export_mesh"
    bl_label = "Export V and C lists"
    bl_description = "Save file with V and C lists"

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
        return context.object and (context.object.type == "MESH")

    def execute(self, context):
        bpy.ops.object.editmode_toggle()
        errors = write_mesh_to_file(
            self.filepath, context, flatten=context.scene.gemlab_flatten
        )
        if errors != "":
            self.report({"WARNING"}, errors)
        bpy.ops.object.editmode_toggle()
        return {"FINISHED"}

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".py")
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
    scene.gemlab_show_etag = bpy.props.BoolProperty(
        name="Edge", description="Display Edge Tags", default=True
    )

    scene.gemlab_show_vtag = bpy.props.BoolProperty(
        name="Vertex", description="Display Vertex Tags", default=True
    )

    scene.gemlab_show_ctag = bpy.props.BoolProperty(
        name="Cell", description="Display Cell Tags", default=True
    )

    # font sizes
    scene.gemlab_vert_font = bpy.props.IntProperty(
        name="V", description="Vertex font size", default=12, min=6, max=100
    )

    scene.gemlab_edge_font = bpy.props.IntProperty(
        name="E", description="Edge font size", default=12, min=6, max=100
    )

    scene.gemlab_cell_font = bpy.props.IntProperty(
        name="C", description="Edge font size", default=20, min=6, max=100
    )

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

    # export data
    scene.gemlab_flatten = bpy.props.BoolProperty(
        name="Project z back to 0",
        description="Project z coordinates back to 0 (flatten)",
        default=False,
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
        lo.prop(sc, "gemlab_flatten")
        lo.operator("gemlab.export_mesh", text="Save .py File")


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
    del bpy.types.Scene.gemlab_flatten
    del bpy.types.WindowManager.do_show_tags
