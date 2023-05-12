import bpy
import bmesh

from ...utils import crash_safe, get_edit_mesh
from ..facemap import (
    FaceMap,
    add_facemap_for_groups,
    verify_facemaps_for_object
)

from .roof_types import create_roof
from .roof_props import RoofProperty


class BTOOLS_OT_add_roof(bpy.types.Operator):
    """Create roof from selected upward facing faces"""

    bl_idname = "btools.add_roof"
    bl_label = "Add Roof"
    bl_options = {"REGISTER", "UNDO", "PRESET"}

    props: bpy.props.PointerProperty(type=RoofProperty)

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.mode == "EDIT_MESH"

    def execute(self, context):
        return build(context, self.props)

    def draw(self, context):
        self.props.draw(context, self.layout)


@crash_safe
def build(context, props):
    verify_facemaps_for_object(context.object)
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    faces = [f for f in bm.faces if f.select]

    # XXX Fix normals if they are inverted(Z-)
    for f in faces:
        if f.normal.z < 0:
            f.normal_flip()

    if validate_roof_faces(bm):
        add_roof_facemaps()
        create_roof(bm, faces, props)
        bmesh.update_edit_mesh(me, loop_triangles=True)
        return {"FINISHED"}

    bmesh.update_edit_mesh(me, loop_triangles=True)
    return {"CANCELLED"}


def add_roof_facemaps():
    add_facemap_for_groups(FaceMap.ROOF)


def validate_roof_faces(bm):
    if faces := [f for f in bm.faces if f.select]:
        if all(round(f.normal.z, 1) for f in faces):
            return True
    return False
