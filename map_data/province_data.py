from multiprocessing import Pool

def init(rgb_rev):
    global global_rgb_rev

    global_rgb_rev = rgb_rev

def worker(*rgbs):
    return [global_rgb_rev[(rgb[0], rgb[1], rgb[2])] for rgb in rgbs]

if __name__ == '__main__':
    def parse_line(line):
        line = line.strip()
        line = line.replace('\t', ' ')
        line = line.replace('{', ' { ')
        line = line.replace('}', ' } ')
        line = line.replace('[', ' [ ')
        line = line.replace(']', ' ] ')
        line = line.replace('!=', ' != ')
        line = line.replace('=', ' = ')
        line = line.replace('>', ' > ')
        line = line.replace('<', ' < ')

        while '  ' in line:
            line = line.replace('  ', ' ')

        line = line.replace('> =', '>=')
        line = line.replace('< =', '<=')
        line = line.replace('= =', '==')
        line = line.replace('! =', '!=')

        comma = False
        comment = False

        for i, char in enumerate(line):
            if char == '#':
                if not comma:
                    line = line[:i]
                    
                    break
            elif char == '"':
                if comma:
                    comma = False
                else:
                    comma = True
            elif char == ' ':
                if comma:
                    line = line[:i] + '%' + line[i + 1:]

        line = line.strip()

        prev = 0
        
        while True:
            start = line.find('[ [', prev)

            if start + 1:
                end = line.find(']', start)
                block = line[start:end + 1]
                block_new = block.replace(' ', '')
                line = line.replace(block, block_new)
                prev = start + len(block_new)
            else:
                break

        if line:
            tokens = line.split(' ')
            tokens = [token.replace('%', ' ') for token in tokens]

            return tokens
        else:
            return []
        

    def parse_file(path):
        with open(path, encoding='utf-8-sig') as f:
            file = list()
            stack = [file]

            for line in f.readlines():
                rhs = False
                
                for token in parse_line(line):
                    if token == '=' or token == '>' or token == '<' or token == '>=' or token == '<=' or token == '==' or token == '!=':
                        rhs = True

                        stack[-1][-1] = [stack[-1][-1], token]
                        stack.append(stack[-1][-1])
                    elif token == '{':
                        rhs = False
                        
                        stack[-1].append(list())

                        if type(stack[-1][0]) == type(str()):
                            stack.append(stack.pop()[-1])
                        else:
                            stack.append(stack[-1][-1])
                    elif token == '}' or token == ']':
                        stack.pop()
                    elif '[[' in token:
                        stack[-1].append([token[1:], list()])
                        stack.append(stack[-1][-1][1])
                    elif 'RANGE' == token or 'LIST' == token:
                        stack[-1].append(token)
                    else:
                        stack[-1].append(token)

                        if rhs:
                            rhs = False

                            stack.pop()

            return file

    def get_neighb(width, height, x, y):
        out = list()

        if x > 0:
            out.append((x - 1, y))
        if x + 1 < width:
            out.append((x + 1, y))
        if y > 0:
            out.append((x, y - 1))
        if y + 1 < height:
            out.append((x, y + 1))

        return out

    from PIL import Image
    from numpy import array
    
    file = parse_file('map_data\\default.map')

    water = set()
    wasteland = set()

    for entry in file:
        if entry[0] == 'sea_zones' or entry[0] == 'river_provinces':
            if entry[2] == 'RANGE':
                for prov in range(int(entry[3][0]), int(entry[3][1]) + 1):
                    water.add(prov)
            elif entry[2] == 'LIST':
                for prov in entry[3]:
                    water.add(int(prov))
        elif entry[0] == 'impassable_mountains':
            if entry[2] == 'RANGE':
                for prov in range(int(entry[3][0]), int(entry[3][1]) + 1):
                    wasteland.add(prov)
            elif entry[2] == 'LIST':
                for prov in entry[3]:
                    wasteland.add(int(prov))

    rgb = dict()

    with open('map_data\\definition.csv', 'rb') as f:
        for line in f.readlines()[1:]:
            line = line.decode("latin-1")
            line = line[:line.find('#')]
            line = line.split(';')

            if len(line) >= 4:
                rgb[int(line[0])] = (int(line[1]), int(line[2]), int(line[3]))
                
    rgb_rev = dict([(v, k) for k, v in rgb.items()])

    neighb = dict()
    port = dict()

    with Image.open('map_data\\provinces.png') as prov:
        pool = Pool(initializer=init, initargs=(rgb_rev,))
        pixel = pool.starmap(worker, array(prov))
        pool.close()

        coord = dict()
                
        for y in range(prov.height):
            for x in range(prov.width):
                p = pixel[y][x]

                if not p in neighb:
                    neighb[p] = set()
                    port[p] = set()
                    coord[p] = [0, [0, 0]]

                coord[p][0] += 1
                coord[p][1][0] += x
                coord[p][1][1] += y

                for entry in get_neighb(prov.width, prov.height, x, y):
                    pp = pixel[entry[1]][entry[0]]

                    if p != pp and not pp in wasteland:
                        if pp in water:
                            if p in water:
                                neighb[p].add(pp)
                            else:
                                port[p].add(pp)
                        else:
                            if p in water:
                                port[p].add(pp)
                            else:
                                neighb[p].add(pp)

        for p, s in coord.items():
            coord[p] = (round(s[1][0] / s[0], 3), round(s[1][1] / s[0], 3))
            
        out = ''

        for prov in rgb:
            loc_coord = ''
            loc_sea = ''
            loc_neighb = ''
            loc_port = ''

            if prov in coord:
                 loc_coord = ' set_variable = { name = prov_x value = %s } set_variable = { name = prov_y value = %s }' % coord[prov]

            if prov in water:
                loc_sea = ' set_variable = { name = prov_sea value = yes } add_to_global_variable_list = { name = every_water target = this }'
            else:
                loc_sea = ' set_variable = { name = prov_sea value = no }'

            if prov in neighb:
                for n in neighb[prov]:
                    loc_neighb += ' add_to_variable_list = { name = prov_neighb target = province:%s }' % n
            if prov in port:
                for p in port[prov]:
                    loc_port += ' add_to_variable_list = { name = prov_port target = province:%s }' % p

            out += 'province:%s = {%s%s%s%s }\n' % (prov, loc_coord, loc_sea, loc_neighb, loc_port)

        with open('out.txt', 'w', encoding='utf-8-sig') as f:
            f.write(out)
