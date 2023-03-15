import bpy, bmesh

import numpy as np
np.set_printoptions(suppress=True)



def obj_from_pydata(name, verts, edges=None, close=True, collection_name=None):
    if edges is None:
        # join vertices into one uninterrupted chain of edges.
        edges = [[i, i + 1] for i in range(len(verts) - 1)]
        if close:
            edges.append([len(verts) - 1, 0])  # connect last to first

    # generate mesh
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, [])

    obj = bpy.data.objects.new(name, me)

    # Move into collection if specified
    if collection_name != None:  # make argument optional

        # collection exists
        collection = bpy.data.collections.get(collection_name)
        if collection:
            bpy.data.collections[collection_name].objects.link(obj)


        else:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)  # link collection to main scene
            bpy.data.collections[collection_name].objects.link(obj)

    return obj



