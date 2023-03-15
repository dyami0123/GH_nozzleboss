from gh_nozzleboss.gcode_lib.GcodeModel import GcodeModel


class GcodeParser:
    comment = ""

    def __init__(self):
        self.model = GcodeModel(self)

    def parseFile(self, path):
        # read the gcode file
        with open(path, 'r') as f:
            # init line counter
            self.lineNb = 0
            # for all lines
            for line in f:
                # inc line counter
                self.lineNb += 1
                # remove trailing linefeed
                self.line = line.rstrip()
                # parse a line
                self.parseLine()

        # self.model.postProcess()
        return self.model

    def parseLine(self):
        # strip comments:
        bits = self.line.split(';', 1)
        if (len(bits) > 1):
            GcodeParser.comment = bits[1]

        # extract & clean command
        command = bits[0].strip()

        # TODO strip logical line number & checksum

        # code is fist word, then args
        comm = command.split(None, 1)
        code = comm[0] if (len(comm) > 0) else None
        args = comm[1] if (len(comm) > 1) else None

        if code:
            if hasattr(self, "parse_ " + code):
                getattr(self, "parse_ " + code)(args)
                # self.parseArgs(args)
            else:
                if code[0] == "T":

                    self.model.toolnumber = int(code[1:])
                    # print(self.model.toolnumber)
                else:
                    pass
                    # print("incorrect gcode")#self.warn("Unknown code '%s'"%code)

    def parseArgs(self, args):
        dic = {}
        if args:
            bits = args.split()
            for bit in bits:
                letter = bit[0]
                try:
                    coord = float(bit[1:])
                except ValueError:
                    coord = 1
                dic[letter] = coord
        return dic

    def parse_G1(self, args, type="G1"):
        # G1: Controlled move
        self.model.do_G1(self.parseArgs(args), type)

    def parse_G0(self, args, type="G0"):
        # G1: Controlled move
        self.model.do_G1(self.parseArgs(args), type)

    def parse_G90(self, args):
        # G90: Set to Absolute Positioning
        self.model.setRelative(False)

    def parse_G91(self, args):
        # G91: Set to Relative Positioning
        self.model.setRelative(True)

    def parse_G92(self, args):
        # G92: Set Position
        self.model.do_G92(self.parseArgs(args))

    # def parse_M163(self, args):
    #         self.model.do_M163(self.parseArgs(args))

    def warn(self, msg):
        print("[WARN] Line %d: %s (Text:'%s')" % (self.lineNb, msg, self.line))

    def error(self, msg):
        print("[ERROR] Line %d: %s (Text:'%s')" % (self.lineNb, msg, self.line))
        raise Exception("[ERROR] Line %d: %s (Text:'%s')" % (self.lineNb, msg, self.line))
