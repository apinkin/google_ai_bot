import sys
import urllib2

"""Code, with no error checking, to parse a PlanetWars game into
   a replayable code file. Argument is game page URL."""
def main(argv):
    input_url = argv[0]
    req = urllib2.Request(input_url)
    response = urllib2.urlopen(req)
    s = response.read()
    PLAYBACK_START = "playback_string="
    PLAYBACK_END = "\\n"
    start_index = s.find(PLAYBACK_START) + len(PLAYBACK_START)
    end_index = s.find(PLAYBACK_END, start_index)
    if end_index == -1:
        end_index = s.find('"', start_index)
    s = s[start_index:end_index]
    planets, moves = s.split("|")

    data = []
    for p in planets.split(":"):
        line = p.split(",")
        if len(line) != 5:
            print "bad line: %s" % p
        x,y,o,n,r = line
        data.append(line)

    np = len(data)

    moves = moves.split(":")

    print("# turn 1")
    for i in xrange(np):
        x,y,o,n,r = data[i]
        print("P %s %s %s %s %s" % (x,y,o,n,r))
    print("go\n")

    for (turn,f) in enumerate(moves):
        print("# turn: %d" % (turn + 2))
        xs = f.split(",")
        for i in xrange(np):
            x,y,o,n,r = data[i]
            tmp = xs[i].strip().split(".")
            if len(tmp) < 2:
                print "error here: ", xs[i]
                break
            o,n = tmp
            print("P %s %s %s %s %s" % (x,y,o,n,r))
        for j in xrange(np,len(xs)):
            u = xs[j].split(".")
            if len(u) != 6:
                #print "er: ", xs[j]
                continue
            o,n,s,d,t,r = u
            print("F %s %s %s %s %s %s" % (o,n,s,d,t,r))
        print("go\n")

if __name__ == "__main__":
    argv = sys.argv[1:]
    main(argv)



