import time
import math
from client import ClientSocket, ByeException

def euclidian_distance(x, y) :
    return ((x[0]-y[0])**2+(x[1]-y[1])**2)**(1/2)

def heuristic(map):
    """Heuristic: Giving value to ennemies around.
    A distance coefficient is used to give priority to closest group.
    An other coefficient is used to favorise smallest group than us.
    The difference of our size and ennemy size (villages not included) is also used
    to emphasize on fighting ennemies.

    Args:
        map (dict): Map

    Returns:
        [float]: the score
    """
    score = 0
    if len(map["A"]) == 0:
        score = -10000
    elif len(map["E"]) == 0:
        score = 10000
    else:
        for ally in map["A"]:
            for i, x in enumerate(map["E"]+map["N"]):
                distance = euclidian_distance(ally, x)
                coef_dist = 1 / math.exp(distance/max(map["size"]))
                coef_num = ally[2] / x[2]
                if i < len(map["E"]):
                    coef_num *= 3
                score += (coef_dist * coef_num)
        score /= len(map["A"])
        total_A = sum(x[2]-1 for x in map["A"])
        total_E = sum(x[2]-1 for x in map["E"])
        score += (total_A - total_E)
    return score

def get_pos(pos1, pos2):
    """Get the direction of pos2 related to pos1

    Args:
        pos1 (tuple): position 1
        pos2 (tuple): position 2

    Returns:
        int, int: direction
    """
    if pos1[0] - pos2[0] > 0: i = -1
    elif pos1[0] - pos2[0] < 0: i = 1
    else: i = 0
    if pos1[1] - pos2[1] > 0: j = -1
    elif pos1[1] - pos2[1] < 0: j = 1
    else: j = 0
    return i,j

def split_proportion(me, E1, E2):
    """[summary]

    Args:
        me (int): size of my group to split
        E1 (int): size of group E1
        E2 (int): size of group E2

    Returns:
        int, int: splitting to make, directed to E1 and E2 
    """
    me1 = int(me * (E1 / (E1 + E2)))
    return me1, me - me1

def add_split_move(my_pos, other_pos, all_moves, turn):
    """Splitting if the two closest ennemies are fewer than the split.

    Args:
        my_pos (tuple): ally position
        other_pos (tuple): ennemies position (villages included)
        all_moves (list): list of all movements, to append the split
        turn ([type]): "A" or "E
    """
    dist_list = []
    for x in other_pos:
        distance = euclidian_distance(my_pos, x)
        dist_list.append((distance, x[0], x[1], x[2]))
    if len(dist_list) >= 2:
        dist_list = sorted(dist_list, key=lambda x: x[0])
        first = dist_list[0]
        second = dist_list[1]
        g1, g2 = split_proportion(my_pos[2], first[3], second[3])
        if g1 > first[3] and g2 > second[3]:
            i,j = get_pos(my_pos, (first[1],first[2],first[3]))
            move1 = (my_pos, (my_pos[0]+i,my_pos[1]+j,g1), turn)
            i,j = get_pos(my_pos, (second[1],second[2],second[3]))
            move2 = (my_pos, (my_pos[0]+i,my_pos[1]+j,g2), turn)
            if move1 != move2:
                all_moves.append([move1, move2])
    
def find_moves(map, is_max):
    """Find moves to do, escape ennemies and splitting included.

    Args:
        map ([type]): Map
        is_max (bool): Turn

    Returns:
        [list]: list of all moves (format : [(pos_initial), (objectif), "A" or "E"])
    """
    turn = "A" if is_max else "E"
    other = "E" if is_max else "A"
    next_pos_indices = []
    all_moves = []
    for my_pos in map[turn]:
        for ind, x in enumerate(map[other]+map[turn]+map["N"]):
            if x != my_pos:
                i, j = get_pos(my_pos, x)
                if (i, j) not in next_pos_indices:
                    next_pos_indices.append((i,j))
                    all_moves.append([(my_pos, (my_pos[0]+i,my_pos[1]+j,my_pos[2]), turn)])
                    
                    # escape against ennemies
                    if ind < len(map[other]) and my_pos[0]-i >= 0 and my_pos[0]-i < map["size"][0] and \
                        my_pos[1]-j >= 0 and my_pos[1]-j < map["size"][1] and (-i,-j) not in next_pos_indices:
                            next_pos_indices.append((-i,-j))
                            all_moves.append([(my_pos, (my_pos[0]-i,my_pos[1]-j,my_pos[2]), turn)])
        add_split_move(my_pos, map["N"]+map[other], all_moves, turn)
    return all_moves

def  proba_win_random_battle(E1, E2):
    """Probabilities of winning

    Args:
        E1 (int): size of group 1
        E2 (int): size of group 2

    Returns:
        [float]: probability E1 wins
    """
    if E1 >= 1.5*E2: return 1
    elif E2 >= 1.5*E1: return 0
    elif E1 == E2: return 0.5
    elif E1 < E2: return E1 / (2 * E2)
    else: return E1 / E2 - 0.5

def reward_decomposed(E1, E2, N):
    """Simulation of a fight between E1 and E2

    Args:
        E1 (int): size of group 1
        E2 (int): size of group 2
        N (bool): True if human, else False

    Returns:
        [list]: ["V" if E1 win, else "L", expected size of the remaining group]
    """
    prob_battle = proba_win_random_battle(E1, E2)
    if N:
        if prob_battle >= 0.5:
            nb_personnes_restante = E1+E2
            return "V", int(nb_personnes_restante)
        else:
            nb_personnes_restante = (1-prob_battle) * E2
            return "L", int(nb_personnes_restante)
    else:
        if prob_battle > 0.5:
            nb_personnes_restante = prob_battle * E1
            return "V", int(nb_personnes_restante)
        else:
            nb_personnes_restante = (1-prob_battle) * E2
            return "L", int(nb_personnes_restante)

def create_map(map, moves):
    """map creation, depending of the move

    Args:
        map (dict): the map
        moves (list): the moves

    Returns:
        [dict]: the new map created
    """
    new_map = {"A":[],"E":[],"N":[], "size":map["size"]}
    turn = moves[0][2]
    other = "E" if turn == "A" else "A"
    first_turn = True
    for move in moves:
        objectif = move[1]
        actual = move[0]
        is_confrontation = False
        for i, x in enumerate(map[turn]+map[other]+map["N"]):
            if x[0] == actual[0] and x[1] == actual[1]:
                pass
            elif x[0] == objectif[0] and x[1] == objectif[1]:
                is_confrontation = True
                if i < len(map[turn]):
                    new_map[turn].append((objectif[0], objectif[1], objectif[2]+x[2]))
                else:
                    if i < len(map[turn])+len(map[other]):
                        reward = reward_decomposed(objectif[2], x[2], False)
                    else:
                        reward = reward_decomposed(objectif[2], x[2], True)
                    if reward[0] == "V":
                        new_map[turn].append((objectif[0], objectif[1], reward[1]))
                    else:
                        new_map[other].append((objectif[0], objectif[1], reward[1]))
            elif first_turn == True:
                if i < len(map[turn]): new_map[turn].append(x)
                elif i >= len(map[turn]) and i < len(map[turn])+len(map[other]): new_map[other].append(x)
                else: new_map["N"].append(x)
        first_turn = False
        if is_confrontation == False:
            new_map[turn].append(objectif)
    return new_map

def alphabeta(map, max_depth, depth, alpha, beta, is_max):
    """ALPHABETA Algorithm

    Args:
        map (dict): {map["A"], map["E"], map["N"], map["size"]}
        max_depth (int): maximum depth
        depth (int): depth level
        alpha (float): alpha for pruning
        beta (float): beta for pruning
        is_max (bool): turn

    Returns:
        [list or int]: return the heuritic value or a list of move for the max depth
    """
    if len(map["A"]) == 0 or len(map["E"]) == 0 or depth == 0:
        return heuristic(map)
    else:
        all_moves = find_moves(map, is_max)
        if is_max == True:
            value = -float("inf")
            if depth == max_depth:
                max_value = -float("inf")  
            for move in all_moves:
                new_map = create_map(map, move)
                value = alphabeta(new_map, max_depth, depth-1, alpha, beta, not is_max)
                del new_map
                if depth == max_depth and value > max_value:
                    max_value = value
                    best_move = move
                if value >= beta:
                    break
            if depth != max_depth:
                return value
            else:
                return best_move
        else:
            value = float("inf")
            for move in all_moves:
                new_map = create_map(map, move)
                value = min(value, alphabeta(new_map, max_depth, depth-1, alpha, beta, not is_max))
                del new_map
                beta = min(beta, value)
                if alpha >= value:
                    break
            return value

def process_message(map, message):
    """Process the message received from the server to update the map

    Args:
        map (dict): map
        message (list): list of move

    Returns:
        dict: The map updated
    """
    if len(message) > 0:
        for y in message:
            message_in = False
            for i, x in enumerate(map):
                if x[0] == y[0] and x[1] == y[1]:
                    map[i] = y
                    message_in = True
            if message_in == False:
                map.append(y)
        to_delete = []
        for i, x in enumerate(map):
            if x[2] == 0 and x[3] == 0 and x[4] == 0:
                to_delete.append(i)
        for i in reversed(to_delete):
            del map[i]
    return map

if __name__ == '__main__':
    
    client_socket = ClientSocket('localhost', 5555)
    client_socket.send_nme("JPG-JeanPaulGabriel")
    
    # set message, size = (nb_row, nb_column)
    message = client_socket.get_message()
    size = (message[1][1], message[1][0])

    # hum message, not used
    message = client_socket.get_message()
    
    # hme message, initial position of your player, initial_pos = (column,row)
    message = client_socket.get_message()
    initial_pos = (message[1])
    
    # map message
    message = client_socket.get_message()
    map = message[1]
    
    # Werewolf or Vampire ?
    werewolf = list(filter(lambda x: x[0] == initial_pos[0] and x[1] == initial_pos[1], map))[0][4]>0

    # start of the game
    while True:
        try:
            message  = client_socket.get_message()
        except ByeException:
            exit("ADIOS")
        
        time_message_received = time.time()
        map = process_message(map, message[1])
        
        if message[0] == "upd":
            # creation du format alphabeta
            x = [(x[0],x[1],x[4]) for x in map if x[4] != 0]
            y = [(y[0],y[1],y[3]) for y in map if y[3] != 0]
            z = [(z[0],z[1],z[2]) for z in map if z[2] != 0]
            if werewolf: new_map = {"A":x, "E":y, "N":z}
            else: new_map = {"A":y, "E":x, "N":z}
            new_map["size"] = size
            
            """
            map structure:
                map["E"]: enemis (format : [(x,y,size of group)])
                map["A"] : amis (format : [(x,y,size of group)])
                map["N"] : humans (format : [(x,y,size of group)])
                map["size"] : size of the map (format: [x,y])
            """
            depth = 4
            
            # alphabeta
            move = alphabeta(new_map, depth, depth, -float("inf"), float("inf"), True)
            #print("===>", move)
            
            # passage du format alphabeta au format serveur
            formated_moves = []
            for m in move:
                formated_moves.append((m[0][0], m[0][1], m[1][2], m[1][0], m[1][1]))
            
            client_socket.send_mov(len(formated_moves), formated_moves)