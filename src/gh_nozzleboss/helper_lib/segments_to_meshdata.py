def segments_to_meshdata(segments):  # edges only on extrusion
    segs = segments
    verts = []
    edges = []
    del_offset = 0  # to travel segs in a row, one gets deleted, need to keep track of index for edges
    for i in range(len(segs)):
        if i >= len(segs) - 1:
            if segs[i].style == 'extrude':
                verts.append([segs[i].coords['X'], segs[i].coords['Y'], segs[i].coords['Z']])

            break

        # start of extrusion for first time
        if segs[i].style == 'travel' and segs[i + 1].style == 'extrude':
            verts.append([segs[i].coords['X'], segs[i].coords['Y'], segs[i].coords['Z']])
            verts.append([segs[i + 1].coords['X'], segs[i + 1].coords['Y'], segs[i + 1].coords['Z']])
            edges.append([i - del_offset, (i - del_offset) + 1])

        # mitte, current and next are extrusion, only add next, current is already in vert list
        if segs[i].style == 'extrude' and segs[i + 1].style == 'extrude':
            verts.append([segs[i + 1].coords['X'], segs[i + 1].coords['Y'], segs[i + 1].coords['Z']])
            edges.append([i - del_offset, (i - del_offset) + 1])

        if segs[i].style == 'travel' and segs[i + 1].style == 'travel':
            del_offset += 1

    return verts, edges


