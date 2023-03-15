
class Segment:
    def __init__(self, type, coords, color, toolnumber, lineNb, line):
        self.type = type
        self.coords = coords
        self.color = color
        self.toolnumber = toolnumber
        self.lineNb = lineNb
        self.line = line
        self.style = None
        self.layerIdx = None

        # self.distance = None
        # self.extrudate = None
    def __str__(self):
        return " <coords=%s, lineNb=%d, style=%s, layerIdx=%d, color=%s " % \
        (str(self.coords), self.lineNb, self.style, self.layerIdx, str(self.color))
