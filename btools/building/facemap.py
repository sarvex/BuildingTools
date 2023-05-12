import bpy
import bmesh

from enum import Enum, auto
from functools import wraps

from ..utils import (
    link_material,
    get_edit_mesh,
    bmesh_from_active_object,
    uv_map_active_editmesh_selection,
)


class AutoIndex(Enum):
    def _generate_next_value_(self, start, count, last_values):
        return count


class FaceMap(AutoIndex):
    """ Enum provides names for face_maps """

    # Buildings
    SLABS = auto()
    WALLS = auto()
    COLUMNS = auto()

    FRAME = auto()

    WINDOW = auto()
    WINDOW_BARS = auto()
    WINDOW_PANES = auto()
    WINDOW_LOUVERS = auto()

    DOOR = auto
    DOOR_PANES = auto()
    DOOR_PANELS = auto()
    DOOR_LOUVERS = auto()

    STAIRS = auto()
    BALCONY = auto()

    RAILING_POSTS = auto()
    RAILING_WALLS = auto()
    RAILING_RAILS = auto()

    ROOF = auto()
    ROOF_HANGS = auto()

    CUSTOM = auto()

    # Roads
    ROAD = auto()
    SHOULDER = auto()
    SIDEWALK = auto()
    SIDEWALK_SIDE = auto()
    SHOULDER_EXTENSION = auto()


def map_new_faces(group, skip=None):
    """Finds all newly created faces in a function and adds them to a face_map
    called group.name.lower()

    if skip is provided, then all faces in the face_map called skip.name
    will not be added to the face_map
    """

    def outer(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            bm = [arg for arg in args if isinstance(arg, bmesh.types.BMesh)].pop()
            faces = set(bm.faces)

            result = func(*args, **kwargs)

            new_faces = set(bm.faces) - faces
            add_faces_to_map(bm, list(new_faces), group, skip)
            return result

        return wrapper

    return outer


def add_faces_to_map(bm, faces, group, skip=None):
    """Sets the face_map index of faces to the index of the face_map called
    group.name.lower()

    see map_new_faces for the option *skip*
    """
    face_map = bm.faces.layers.face_map.active
    group_index = face_map_index_from_name(group.name.lower())

    def remove_skipped(f):
        if skip:
            skip_index = face_map_index_from_name(skip.name.lower())
            return f[face_map] != skip_index
        return True

    for face in list(filter(remove_skipped, faces)):
        face[face_map] = group_index

    obj = bpy.context.object

    # -- if auto uv map is set, perform UV Mapping for given faces
    if obj.facemap_materials[group_index].auto_map:
        map_method = obj.facemap_materials[group_index].uv_mapping_method
        uv_map_active_editmesh_selection(faces, map_method)

    # -- if the facemap already has a material assigned, assign the new faces to the material
    mat = obj.facemap_materials[group_index].material
    mat_id = [idx for idx, m in enumerate(obj.data.materials) if m == mat]
    if mat_id:
        for f in faces:
            f.material_index = mat_id[-1]


def add_facemap_for_groups(groups):
    """Creates a face_map called group.name.lower if none exists
    in the active object
    """
    obj = bpy.context.object
    groups = groups if isinstance(groups, (list, tuple)) else [groups]

    for group in groups:
        if not obj.face_maps.get(group.name.lower()):
            obj.face_maps.new(name=group.name.lower())
            obj.facemap_materials.add()


def verify_facemaps_for_object(obj):
    """Ensure object has a facemap layer"""
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)
    bm.faces.layers.face_map.verify()
    bmesh.update_edit_mesh(me, loop_triangles=True)


def set_material_for_active_facemap(material, context):
    """Set `material` on all the faces for the current/active facemap"""
    obj = context.object
    index = obj.face_maps.active_index
    active_facemap = obj.face_maps[index]

    link_material(obj, material)
    mat_id = [idx for idx, mat in enumerate(obj.data.materials) if mat == material].pop()

    with bmesh_from_active_object(context) as bm:

        face_map = bm.faces.layers.face_map.active
        for face in bm.faces:
            if face[face_map] == active_facemap.index:
                face.material_index = mat_id


def clear_material_for_active_facemap(context):
    """Remove the material on all faces for the current/active facemap"""
    obj = context.object
    index = obj.face_maps.active_index
    active_facemap = obj.face_maps[index]

    with bmesh_from_active_object(context) as bm:

        face_map = bm.faces.layers.face_map.active
        for face in bm.faces:
            if face[face_map] == active_facemap.index:
                face.material_index = 0


def face_map_index_from_name(name):
    """Get the index of a facemap from its name"""
    return next(
        (
            fmap.index
            for _, fmap in bpy.context.object.face_maps.items()
            if fmap.name == name
        ),
        -1,
    )


def clear_empty_facemaps(context):
    """Remove all facemaps that don't have any faces assigned"""
    obj = context.object
    with bmesh_from_active_object(context) as bm:

        face_map = bm.faces.layers.face_map.active
        used_indices = {f[face_map] for f in bm.faces}
        all_indices = {f.index for f in obj.face_maps}
        tag_remove_indices = all_indices - used_indices

        # -- remove face maps
        tag_remove_maps = [obj.face_maps[idx] for idx in tag_remove_indices]
        for fmap in tag_remove_maps:
            obj.face_maps.remove(fmap)

        # -- remove facemap materials:
        for idx in reversed(list(tag_remove_indices)):
            obj.facemap_materials.remove(idx)


def find_faces_without_facemap(bm):
    """Find all the faces in bm that don't belong to any facemap"""
    face_map = bm.faces.layers.face_map.active
    return [f for f in bm.faces if f[face_map] < 0]