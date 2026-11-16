
import os, json, urllib.request

ENV = os.environ["MAKEFUN_ENV_URL"]
W = 1  # verbose off

# --- board: 0x88-ish mailbox 10x12 ---
# piece values
PV = {'P':100,'N':320,'B':330,'R':500,'Q':900,'K':0}
# piece-square tables (from white's perspective, rank 8 first) - compact midgame PSTs
PST_P = [
 0,  0,  0,  0,  0,  0,  0,  0,
50, 50, 50, 50, 50, 50, 50, 50,
10, 10, 20, 30, 30, 20, 10, 10,
 5,  5, 10, 25, 25, 10,  5,  5,
 0,  0,  0, 20, 20,  0,  0,  0,
 5, -5,-10,  0,  0,-10, -5,  5,
 5, 10, 10,-20,-20, 10, 10,  5,
 0,  0,  0,  0,  0,  0,  0,  0]
PST_N = [
-50,-40,-30,-30,-30,-30,-40,-50,
-40,-20,  0,  0,  0,  0,-20,-40,
-30,  0, 10, 15, 15, 10,  0,-30,
-30,  5, 15, 20, 20, 15,  5,-30,
-30,  0, 15, 20, 20, 15,  0,-30,
-30,  5, 10, 15, 15, 10,  5,-30,
-40,-20,  0,  5,  5,  0,-20,-40,
-50,-40,-30,-30,-30,-30,-40,-50]
PST_B = [
-20,-10,-10,-10,-10,-10,-10,-20,
-10,  0,  0,  0,  0,  0,  0,-10,
-10,  0,  5, 10, 10,  5,  0,-10,
-10,  5,  5, 10, 10,  5,  5,-10,
-10,  0, 10, 10, 10, 10,  0,-10,
-10, 10, 10, 10, 10, 10, 10,-10,
-10,  5,  0,  0,  0,  0,  5,-10,
-20,-10,-10,-10,-10,-10,-10,-20]
PST_R = [
  0,  0,  0,  0,  0,  0,  0,  0,
  5, 10, 10, 10, 10, 10, 10,  5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
  0,  0,  0,  5,  5,  0,  0,  0]
PST_Q = [
-20,-10,-10, -5, -5,-10,-10,-20,
-10,  0,  0,  0,  0,  0,  0,-10,
-10,  0,  5,  5,  5,  5,  0,-10,
 -5,  0,  5,  5,  5,  5,  0, -5,
  0,  0,  5,  5,  5,  5,  0, -5,
-10,  5,  5,  5,  5,  5,  0,-10,
-10,  0,  5,  0,  0,  0,  0,-10,
-20,-10,-10, -5, -5,-10,-10,-20]
PST_K = [
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
-20,-30,-30,-40,-40,-30,-30,-20,
-10,-20,-20,-20,-20,-20,-20,-10,
 20, 20,  0,  0,  0,  0, 20, 20,
 20, 30, 10,  0,  0, 10, 30, 20]
PST = {'P':PST_P,'N':PST_N,'B':PST_B,'R':PST_R,'Q':PST_Q,'K':PST_K}

def fen_board(fen):
    parts = fen.split()
    board = {}
    rows = parts[0].split('/')
    for r, row in enumerate(rows):
        f = 0
        for ch in row:
            if ch.isdigit():
                f += int(ch)
            else:
                sq = (7-r)*8 + f
                board[sq] = ch
                f += 1
    return board, parts[1] == 'w', parts[2], (name_sq(parts[3][:2]) if len(parts) > 3 and parts[3] != '-' else None)

def sq_name(s):
    return "abcdefgh"[s%8] + str(s//8 + 1)

def name_sq(nm):
    return (int(nm[1]) - 1)*8 + "abcdefgh".index(nm[0])

# move gen on dict board
N_OFF = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
K_OFF = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
B_DIR = [(-1,-1),(-1,1),(1,-1),(1,1)]
R_DIR = [(-1,0),(1,0),(0,-1),(0,1)]

def gen_moves(board, wtm, castling, ep):
    moves = []
    own = str.isupper if wtm else str.islower
    for s, p in list(board.items()):
        if p.isupper() != wtm:
            continue
        pt = p.upper()
        r, f = divmod(s, 8)
        if pt == 'P':
            dr = 1 if wtm else -1
            start = 1 if wtm else 6
            prom = 7 if wtm else 0
            t = s + dr*8
            if 0 <= t < 64 and t not in board:
                if t//8 == prom:
                    for pc in 'QRBN':
                        moves.append((s, t, pc))
                else:
                    moves.append((s, t, None))
                    if r == start and s + dr*16 not in board:
                        moves.append((s, s + dr*16, None))
            for df in (-1, 1):
                tt = t + df
                tr, tf = divmod(tt, 64) if False else (None, None)
                if 0 <= tt < 64 and (tt//8 == r + dr) and abs((tt%8) - (s%8)) == 1:
                    q = board.get(tt)
                    if q and not own(q):
                        if tt//8 == prom:
                            for pc in 'QRBN':
                                moves.append((s, tt, pc))
                        else:
                            moves.append((s, tt, None))
                    elif ep is not None and tt == ep and (tt//8 == 5 if wtm else tt//8 == 2):
                        moves.append((s, tt, None))
        elif pt == 'N':
            for dr, df in N_OFF:
                rr, ff = r+dr, f+df
                if 0 <= rr < 8 and 0 <= ff < 8:
                    t = rr*8+ff
                    q = board.get(t)
                    if not q or not own(q):
                        moves.append((s, t, None))
        elif pt == 'K':
            for dr, df in K_OFF:
                rr, ff = r+dr, f+df
                if 0 <= rr < 8 and 0 <= ff < 8:
                    t = rr*8+ff
                    q = board.get(t)
                    if not q or not own(q):
                        moves.append((s, t, None))
            # castling
            rank = 0 if wtm else 7
            rights = 'KQ' if wtm else 'kq'
            if board.get(rank*8+4) == ('K' if wtm else 'k'):
                if rights[0] in castling and (rank*8+5) not in board and (rank*8+6) not in board:
                    if not attacked(board, rank*8+4, not wtm) and not attacked(board, rank*8+5, not wtm) and not attacked(board, rank*8+6, not wtm):
                        moves.append((s, rank*8+6, None))
                if rights[1] in castling and (rank*8+3) not in board and (rank*8+2) not in board and (rank*8+1) not in board:
                    if not attacked(board, rank*8+4, not wtm) and not attacked(board, rank*8+3, not wtm) and not attacked(board, rank*8+2, not wtm):
                        moves.append((s, rank*8+2, None))
        else:
            dirs = B_DIR if pt == 'B' else R_DIR if pt == 'R' else B_DIR + R_DIR
            for dr, df in dirs:
                rr, ff = r+dr, f+df
                while 0 <= rr < 8 and 0 <= ff < 8:
                    t = rr*8+ff
                    q = board.get(t)
                    if not q:
                        moves.append((s, t, None))
                    else:
                        if not own(q):
                            moves.append((s, t, None))
                        break
                    rr += dr; ff += df
    return moves

def attacked(board, sq, by_white):
    # is sq attacked by side by_white
    r, f = divmod(sq, 8)
    # pawns
    dr = -1 if by_white else 1  # attacker pawn sits at sq+dr (white pawn below attacks up)
    for df in (-1, 1):
        rr, ff = r+dr, f+df
        if 0 <= rr < 8 and 0 <= ff < 8:
            p = board.get(rr*8+ff)
            if p and p.upper() == 'P' and (p.isupper() == by_white):
                return True
    for dr, df in N_OFF:
        rr, ff = r+dr, f+df
        if 0 <= rr < 8 and 0 <= ff < 8:
            p = board.get(rr*8+ff)
            if p and p.upper() == 'N' and (p.isupper() == by_white):
                return True
    for dr, df in K_OFF:
        rr, ff = r+dr, f+df
        if 0 <= rr < 8 and 0 <= ff < 8:
            p = board.get(rr*8+ff)
            if p and p.upper() == 'K' and (p.isupper() == by_white):
                return True
    for dirs, pts in ((B_DIR, 'BQ'), (R_DIR, 'RQ')):
        for dr, df in dirs:
            rr, ff = r+dr, f+df
            while 0 <= rr < 8 and 0 <= ff < 8:
                p = board.get(rr*8+ff)
                if p:
                    if p.upper() in pts and (p.isupper() == by_white):
                        return True
                    break
                rr += dr; ff += df
    return False

def king_sq(board, wtm):
    k = 'K' if wtm else 'k'
    for s, p in board.items():
        if p == k: return s
    return -1

def make_move(board, mv, wtm, castling, ep):
    s, t, promo = mv
    b = dict(board)
    p = b.pop(s)
    cap = b.get(t)
    b[t] = (promo if wtm else promo.lower()) if promo else p
    # castling rook move
    if p.upper() == 'K' and abs(t - s) == 2:
        r = s // 8
        if t > s:
            b[r*8+5] = b.pop(r*8+7)
        else:
            b[r*8+3] = b.pop(r*8+0)
    # en passant capture
    if p.upper() == 'P' and t == ep and cap is None and (t % 8) != (s % 8):
        cap = b.pop(t - 8 if wtm else t + 8)
    # new castling rights
    c = castling
    if p == 'K': c = c.replace('K', '').replace('Q', '')
    if p == 'k': c = c.replace('k', '').replace('q', '')
    if s == 7 or t == 7: c = c.replace('K', '')
    if s == 0 or t == 0: c = c.replace('Q', '')
    if s == 63 or t == 63: c = c.replace('k', '')
    if s == 56 or t == 56: c = c.replace('q', '')
    # new ep square
    e = None
    if p.upper() == 'P' and abs(t - s) == 16:
        e = (s + t) // 2
    return b, cap, c, e

def evaluate(board, wtm):
    score = 0
    for s, p in board.items():
        pt = p.upper()
        v = PV[pt] + PST[pt][(7 - s//8)*8 + s%8 if p.isupper() else s]
        score += v if p.isupper() else -v
    return score if wtm else -score

NODES = 0

def quiesce(board, wtm, castling, ep, alpha, beta, d=0):
    global NODES
    NODES += 1
    stand = evaluate(board, wtm)
    if d >= 4:
        return stand
    if stand >= beta:
        return beta
    if stand > alpha:
        alpha = stand
    # captures only
    caps = [m for m in gen_moves(board, wtm, castling, ep) if m[1] in board or (board.get(m[0],'').upper()=='P' and m[1]==ep)]
    # MVV-LVA order
    def capval(m):
        v = board.get(m[1])
        return (PV.get(v.upper(), 0) if v else 100) - PV[board[m[0]].upper()]//10
    caps.sort(key=capval, reverse=True)
    for m in caps:
        nb, cap, nc, ne = make_move(board, m, wtm, castling, ep)
        if cap is None and m[1] != ep:
            continue
        sc = -quiesce(nb, not wtm, nc, ne, -beta, -alpha, d+1)
        if sc >= beta:
            return beta
        if sc > alpha:
            alpha = sc
    return alpha

def alphabeta(board, wtm, castling, ep, depth, alpha, beta, ply):
    global NODES
    NODES += 1
    if depth <= 0:
        return quiesce(board, wtm, castling, ep, alpha, beta)
    # null-move pruning
    if depth >= 3 and ply > 0 and any(p.upper() != 'K' and p.upper() != 'P' for p in board.values()):
        sc = -alphabeta(board, not wtm, castling, ep, depth-3, -beta, -beta+1, ply+1)
        if sc >= beta:
            return beta
    best = -10**9
    moves = gen_moves(board, wtm, castling, ep)
    # order: captures first
    def mval(m):
        v = board.get(m[1])
        s = (PV.get(v.upper(), 0)*10 if v else 0) - PV[board[m[0]].upper()]
        if m[2]: s += 800
        return s
    moves.sort(key=mval, reverse=True)
    legal = 0
    for m in moves:
        nb, cap, nc, ne = make_move(board, m, wtm, castling, ep)
        if king_sq(nb, wtm) >= 0 and attacked(nb, king_sq(nb, wtm), not wtm):
            continue
        legal += 1
        sc = -alphabeta(nb, not wtm, nc, ne, depth-1, -beta, -alpha, ply+1)
        if sc >= beta:
            return beta
        if sc > best:
            best = sc
            if sc > alpha:
                alpha = sc
    if legal == 0:
        ks = king_sq(board, wtm)
        if attacked(board, ks, not wtm):
            return -100000 + ply
        return 0
    return best

def best_move(board, wtm, castling, ep, node_budget):
    global NODES
    moves = gen_moves(board, wtm, castling, ep)
    best = None
    depth = 1
    root_moves = []
    for m in moves:
        nb, cap, nc, ne = make_move(board, m, wtm, castling, ep)
        if king_sq(nb, wtm) >= 0 and attacked(nb, king_sq(nb, wtm), not wtm):
            continue
        root_moves.append(m)
    if not root_moves:
        return None
    while depth <= 12 and NODES < node_budget:
        scored = []
        alpha = -10**9
        for m in root_moves:
            nb, cap, nc, ne = make_move(board, m, wtm, castling, ep)
            NODES += 1
            sc = -alphabeta(nb, not wtm, nc, ne, depth-1, -10**9, -alpha, 1)
            scored.append((sc, m))
            if sc > alpha:
                alpha = sc
            if NODES >= node_budget:
                break
        scored.sort(reverse=True)
        if scored and NODES < node_budget:
            best = scored[0][1]
            root_moves = [m for _, m in scored]
        elif scored and best is None:
            best = scored[0][1]
        depth += 1
    if best is None and root_moves:
        best = root_moves[0]
    return best

def mv_uci(m):
    return sq_name(m[0]) + sq_name(m[1]) + (m[2].lower() if m[2] else '')

def post(path, body):
    req = urllib.request.Request(ENV + path, data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=15))

def main():
    while True:
        g = post('/game', {})
        if g.get('status') == 'done':
            break
        # budget by rung
        opp = g.get('opponent_name', '')
        # default budget; tune per opponent rung
        budget = 300000
        if 'depth-2' in str(g.get('opponent')): budget = 40000
        elif 'depth-3' in str(g.get('opponent')): budget = 90000
        elif 'depth-4' in str(g.get('opponent')): budget = 160000
        board, wtm, castling, ep = fen_board(g['fen'])
        colour = g.get('colour') == 'white'
        while g.get('status') == 'your_move':
            NODES = 0
            m = best_move(board, wtm, castling, ep, budget)
            if m is None:
                post('/resign', {'game': g['game']})
                break
            g = post('/move', {'game': g['game'], 'move': mv_uci(m)})
            if g.get('status') == 'done' or g.get('outcome'):
                break
            if g.get('status') == 'your_move':
                board, wtm, castling, ep = fen_board(g['fen'])
                colour = g.get('colour') == 'white'
        if g.get('status') == 'done':
            break

if __name__ == '__main__':
    main()
