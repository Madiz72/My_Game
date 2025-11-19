import pygame
import sys
import random
import math
from collections import deque, Counter

# ---------- تنظیمات اولیه ----------
pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass

W, H = 1100, 700
WIN = pygame.display.set_mode((W, H))
pygame.display.set_caption("RPS: TACTICS — Cyberpunk")
CLOCK = pygame.time.Clock()
FPS = 60

# ---------- رنگ‌ها ----------
NEON_BG = (8, 10, 16)
GRID_NEON = (18, 30, 60)
ACCENT = (110, 200, 255)
ACCENT_PINK = (255, 100, 200)
CARD_BASE = (20, 28, 40)
CARD_EDGE = (45, 60, 80)
TEXT = (220, 235, 255)
HP_FILL = (255, 90, 90)
MANA_FILL = (120, 220, 255)
PARTICLE = (180, 255, 255)

# ---------- فونت ----------
pygame.font.init()
FONT = pygame.font.SysFont("Consolas", 18)
BIG = pygame.font.SysFont("Consolas", 28)
TITLE = pygame.font.SysFont("Consolas", 42, bold=True)

# ---------- صداها (اختیاری) ----------
def load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

sound_play = load_sound("sounds/play.wav")
sound_hit = load_sound("sounds/hit.wav")
sound_win = load_sound("sounds/win.wav")

# ---------- کارت‌ها (تعاریف) ----------
CARD_TEMPLATES = {
    "Rock":     {"cost":1, "base":"Rock",     "dmg":1, "special":None, "color":(200,80,80)},
    "Paper":    {"cost":1, "base":"Paper",    "dmg":1, "special":None, "color":(80,160,255)},
    "Scissors": {"cost":1, "base":"Scissors", "dmg":1, "special":None, "color":(255,200,80)},
    "Rock2":    {"cost":2, "base":"Rock",     "dmg":2, "special":None, "color":(220,100,100)},
    "Paper2":   {"cost":2, "base":"Paper",    "dmg":2, "special":None, "color":(100,190,255)},
    "Scissors2":{"cost":2, "base":"Scissors", "dmg":2, "special":None, "color":(255,210,100)},
    "Shield":   {"cost":1, "base":None,       "dmg":0, "special":"Shield", "color":(200,160,255)},
    "Wild":     {"cost":2, "base":None,       "dmg":1, "special":"Wild",   "color":(160,255,200)},
    "Hack":     {"cost":2, "base":None,       "dmg":0, "special":"Hack",   "color":(255,120,220)},
}

BEATS = {"Rock":"Scissors","Scissors":"Paper","Paper":"Rock"}

def rps_result(a, b):
    # a,b can be "Rock"/"Paper"/"Scissors" or None
    if a is None or b is None:
        return 0
    if a == b: return 0
    return 1 if BEATS[a] == b else -1

class Card:
    def __init__(self, key):
        tpl = CARD_TEMPLATES[key]
        self.key = key
        self.cost = tpl["cost"]
        self.base = tpl["base"]
        self.dmg = tpl["dmg"]
        self.special = tpl["special"]
        self.color = tpl["color"]

    def __repr__(self):
        return f"<Card {self.key}>"

#player deck
class Player:
    def __init__(self, name, deck_list, hp=8, mana=3, max_mana=10):
        self.name = name
        self.deck = deque(deck_list[:])
        random.shuffle(self.deck)
        self.discard = deque()
        self.hand = []
        self.hp = hp
        self.mana = mana
        self.max_mana = max_mana
        self.shield = False
        self.history = []  # names of played cards
        self.shake_offset = (0,0)
        # new: flag to indicate we've auto-boosted mana this turn because of no-playable-card
        self._auto_mana_boosted = False

    def draw(self, n=1, hand_limit=5):
        for _ in range(n):
            if len(self.hand) >= hand_limit: break
            if not self.deck:
                # reshuffle discard
                self.deck = self.discard
                self.discard = deque()
                tmp = list(self.deck)
                random.shuffle(tmp)
                self.deck = deque(tmp)
            if not self.deck: break
            self.hand.append(Card(self.deck.popleft()))

    def play_from_hand(self, idx):
        if 0 <= idx < len(self.hand):
            c = self.hand.pop(idx)
            self.discard.append(c.key)
            self.history.append(c.key)
            # reset auto-boost flag when player actually plays
            self._auto_mana_boosted = False
            return c
        return None

#AI
class AI:
    def __init__(self, kind="beginner"):
        self.kind = kind

    def choose(self, ai_state: Player, opp_state: Player, mana):
        # Build temp hand from actual hand or deck peek
        temp = list(ai_state.hand)
        if not temp:
            for name in list(ai_state.deck)[:5]:
                temp.append(Card(name))
        temp = [c for c in temp if c.cost <= mana]
        if not temp:
            return None
        if self.kind == "beginner":
            return random.choice(temp).key
        if self.kind == "trickster":
            wilds = [c for c in temp if c.special == "Wild"]
            if wilds and random.random() < 0.35:
                return random.choice(wilds).key
            hacks = [c for c in temp if c.special == "Hack"]
            if hacks and random.random() < 0.15:
                return random.choice(hacks).key
            return random.choice(temp).key
        if self.kind == "predictive":
            if not opp_state.history:
                return random.choice(temp).key
            base_counts = Counter()
            for n in opp_state.history:
                b = CARD_TEMPLATES.get(n, {}).get("base")
                if b: base_counts[b] += 1
            if base_counts:
                most = base_counts.most_common(1)[0][0]
                counter = {"Rock":"Paper","Paper":"Scissors","Scissors":"Rock"}[most]
                cands = [c for c in temp if c.base == counter]
                if cands: return random.choice(cands).key
            return random.choice(temp).key
        return random.choice(temp).key

# Particle scene
particles = []
def spawn_particles(x,y,color,amount=18):
    for _ in range(amount):
        ang = random.random()*math.tau
        sp = random.uniform(1.5,5.0)
        life = random.randint(20,45)
        particles.append([x,y, math.cos(ang)*sp, math.sin(ang)*sp, life, color])

def update_particles(surf):
    for p in particles[:]:
        p[0]+=p[2]; p[1]+=p[3]; p[4]-=1
        a = max(0, min(255, int(255*(p[4]/45))))
        s = pygame.Surface((6,6), pygame.SRCALPHA)
        s.fill((*p[5],a))
        surf.blit(s,(p[0]-3,p[1]-3))
        if p[4] <=0:
            particles.remove(p)

# Lazer animation
laser_timers = []  # list of (start_pos,end_pos, ttl)

def spawn_laser(a,b,ttl=18):
    laser_timers.append([a,b,ttl])

def update_draw_lasers(surf):
    for L in laser_timers[:]:
        a,b,ttl = L
        alpha = int(220 * (ttl/18))
        # glow layers
        s = pygame.Surface((W,H), pygame.SRCALPHA)
        pygame.draw.line(s, (*ACCENT, alpha), a, b, 10)
        pygame.draw.line(s, (*ACCENT_PINK, alpha//2), a, b, 4)
        surf.blit(s,(0,0))
        L[2]-=1
        if L[2] <= 0:
            laser_timers.remove(L)

# Simple missions
CAMPAIGN = [
    {"name":"Neon Initiate","ai":"beginner","enemy_deck":["Rock"]*4 + ["Paper"]*3 + ["Scissors"]*3 + ["Shield"]*2 + ["Wild"]},
    {"name":"Predictive Grid","ai":"predictive","enemy_deck":["Rock","Paper","Scissors"]*3 + ["Paper2","Scissors2"] + ["Shield"]},
    {"name":"Chaos Node","ai":"trickster","enemy_deck":["Rock","Paper","Scissors"]*2 + ["Wild"]*4 + ["Hack","Shield"]},
]

# Last mission
def make_player_deck():
    # balanced deck: more 1-cost base cards to avoid dead-hand
    base = ["Rock","Paper","Scissors"]*3 + ["Rock2","Paper2","Scissors2"] + ["Shield","Wild","Hack"]
    deck = base[:]
    random.shuffle(deck)
    return deck

#resolve turn
def resolve_round(player_card: Card, enemy_card: Card, player: Player, enemy: Player):
    msgs = []
    # special Hack handling (steal mana)
    if player_card.special == "Hack":
        stolen = 0
        if enemy.mana > 0:
            enemy.mana = max(0, enemy.mana-1); player.mana = min(player.max_mana, player.mana+1); stolen=1
            msgs.append("Hack succeeded: +1 mana stolen!")
        else:
            msgs.append("Hack failed: enemy had no mana.")
    if enemy_card.special == "Hack":
        if player.mana > 0:
            player.mana = max(0, player.mana-1); enemy.mana = min(enemy.max_mana, enemy.mana+1)
    # Wild auto-win
    if player_card.special == "Wild" and enemy_card.special != "Wild":
        winner = 1
    elif enemy_card.special == "Wild" and player_card.special != "Wild":
        winner = -1
    else:
        winner = rps_result(player_card.base, enemy_card.base)
    # compute damage
    p_dmg = player_card.dmg if winner == 1 else 0
    e_dmg = enemy_card.dmg if winner == -1 else 0
    msgs.append(f"You played {player_card.key}. Enemy played {enemy_card.key}.")
    if winner == 1:
        msgs.append("You win the round!")
        if enemy.shield:
            msgs.append("Enemy shield blocked the damage!")
            enemy.shield = False
            p_dmg = 0
        if p_dmg>0:
            enemy.hp = max(0, enemy.hp - p_dmg)
            msgs.append(f"Enemy took {p_dmg} damage.")
    elif winner == -1:
        msgs.append("Enemy wins the round.")
        if player.shield:
            msgs.append("Your shield blocked the damage!")
            player.shield = False
            e_dmg = 0
        if e_dmg>0:
            player.hp = max(0, player.hp - e_dmg)
            msgs.append(f"You took {e_dmg} damage.")
    else:
        msgs.append("Round tied.")
    # set shield if played
    if player_card.special == "Shield":
        player.shield = True; msgs.append("You gained a shield.")
    if enemy_card.special == "Shield":
        enemy.shield = True; msgs.append("Enemy gained a shield.")
    return msgs

#Neon background
def draw_neon_background(surface, t):
    surface.fill(NEON_BG)
    # grid lines perspective
    spacing = 36
    alpha = 40
    for x in range(0, W, spacing):
        s = pygame.Surface((2, H), pygame.SRCALPHA)
        s.fill((*GRID_NEON, alpha))
        surface.blit(s, (x, 0))
    for y in range(0, H, spacing):
        s = pygame.Surface((W, 2), pygame.SRCALPHA)
        s.fill((*GRID_NEON, alpha))
        surface.blit(s, (0, y))
    # moving subtle noise glow
    glow = pygame.Surface((W, H), pygame.SRCALPHA)
    gx = int(math.sin(t*0.001)*80)
    pygame.draw.circle(glow, (30,60,90,40), (W//2+gx, H//2), 300)
    surface.blit(glow, (0,0), special_flags=pygame.BLEND_ADD)

#holographic card
CARD_W, CARD_H = 140, 190
HAND_Y = H - CARD_H - 36
def render_card_surface(card: Card, selected=False):
    s = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    # base rounded rect
    rr = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    pygame.draw.rect(rr, (*CARD_BASE, 200), (0,0,CARD_W,CARD_H), border_radius=14)
    pygame.draw.rect(rr, (*CARD_EDGE, 120), (4,4,CARD_W-8,CARD_H-8), border_radius=12)
    s.blit(rr, (0,0))
    # holographic header strip
    header = pygame.Surface((CARD_W, 48), pygame.SRCALPHA)
    grad = pygame.Surface((CARD_W,48), pygame.SRCALPHA)
    for i in range(CARD_W):
        a = 60 + int(80 * (i/CARD_W))
        grad.fill((ACCENT[0], ACCENT[1], ACCENT[2], a), (i,0,1,48))
    header.blit(grad,(0,0), special_flags=pygame.BLEND_ADD)
    s.blit(header, (0,0))
    # name text
    name_text = BIG.render(card.key, True, TEXT)
    s.blit(name_text, (10,10))
    # center big icon circle
    cx, cy = CARD_W//2, CARD_H//2 + 8
    pygame.draw.circle(s, (*card.color, 160), (cx, cy), 44)
    inner = pygame.Surface((80,80), pygame.SRCALPHA)
    pygame.draw.circle(inner, (255,255,255,20), (40,40), 40)
    inner2 = pygame.Surface((80,80), pygame.SRCALPHA)
    pygame.draw.circle(inner2, (255,255,255,8), (40,40), 32)
    s.blit(inner, (cx-40, cy-40), special_flags=pygame.BLEND_ADD)
    s.blit(inner2, (cx-40, cy-40), special_flags=pygame.BLEND_ADD)
    # cost box
    pygame.draw.rect(s, (10,10,14,200), (8, CARD_H-36, 48, 28), border_radius=6)
    cost_text = FONT.render(str(card.cost), True, ACCENT)
    s.blit(cost_text, (20, CARD_H-30))
    # special marker
    if card.special:
        sp = FONT.render(card.special, True, ACCENT_PINK)
        s.blit(sp, (CARD_W-10-sp.get_width(), CARD_H-30))
    # selected glow
    if selected:
        g = pygame.Surface((CARD_W+8, CARD_H+8), pygame.SRCALPHA)
        pygame.draw.rect(g, (255,220,160,80), (-4,-4,CARD_W+8,CARD_H+8), border_radius=16)
        s.blit(g, (-4,-4), special_flags=pygame.BLEND_ADD)
    return s

#UI
def draw_ui(player: Player, enemy: Player, campaign_step, messages, selected_idx, hand_surfaces, enemy_preview_count):
    # top HUD
    title = TITLE.render("RPS: TACTICS — Neon Grid", True, ACCENT)
    WIN.blit(title, (24, 12))
    # stage
    st = FONT.render(f"Stage: {campaign_step['name']}  AI: {campaign_step['ai']}", True, TEXT)
    WIN.blit(st, (24, 64))
    # enemy box
    ex = W-360; ey = 20; ew = 340; eh = 150
    pygame.draw.rect(WIN, (12,16,22,220), (ex,ey,ew,eh), border_radius=10)
    WIN.blit(FONT.render(f"Enemy HP: ", True, TEXT), (ex+12, ey+12))
    # HP bar
    hp_w = 220; hp_h = 18
    hp_x = ex+12; hp_y = ey+40
    pygame.draw.rect(WIN, (40,40,45), (hp_x,hp_y,hp_w,hp_h), border_radius=8)
    hp_ratio = enemy.hp / 10.0
    pygame.draw.rect(WIN, HP_FILL, (hp_x,hp_y,int(hp_w*hp_ratio),hp_h), border_radius=8)
    WIN.blit(FONT.render(f"{enemy.hp}/10", True, TEXT), (hp_x+hp_w+8, hp_y-2))
    # enemy mana bar
    WIN.blit(FONT.render("Mana: ", True, TEXT), (ex+12, hp_y+30))
    mana_w = 220; mana_h = 12
    m_y = hp_y+54
    pygame.draw.rect(WIN, (30,30,35), (hp_x,m_y,mana_w,mana_h), border_radius=6)
    pygame.draw.rect(WIN, MANA_FILL, (hp_x,m_y,int(mana_w*(enemy.mana/enemy.max_mana)),mana_h), border_radius=6)
    WIN.blit(FONT.render(f"{enemy.mana}", True, TEXT), (hp_x+mana_w+8, m_y-3))
    WIN.blit(FONT.render(f"Deck: {len(enemy.deck)}  Discard: {len(enemy.discard)}", True, TEXT), (ex+12, m_y+22))
    # player HUD bottom-left
    pygame.draw.rect(WIN, (10,12,18,200), (12, H-170, 360, 156), border_radius=10)
    WIN.blit(FONT.render(f"Player HP: ", True, TEXT), (28, H-154))
    p_hp_x = 28; p_hp_y = H-128; p_hp_w = 200; p_hp_h = 18
    pygame.draw.rect(WIN, (40,40,45), (p_hp_x,p_hp_y,p_hp_w,p_hp_h), border_radius=8)
    pygame.draw.rect(WIN, HP_FILL, (p_hp_x,p_hp_y,int(p_hp_w*(player.hp/10.0)),p_hp_h), border_radius=8)
    WIN.blit(FONT.render(f"{player.hp}/10", True, TEXT), (p_hp_x+p_hp_w+8, p_hp_y-2))
    WIN.blit(FONT.render("Mana:", True, TEXT), (28, p_hp_y+30))
    pygame.draw.rect(WIN, (30,30,35), (p_hp_x, p_hp_y+36, p_hp_w, 12), border_radius=6)
    pygame.draw.rect(WIN, MANA_FILL, (p_hp_x, p_hp_y+36, int(p_hp_w*(player.mana/player.max_mana)), 12), border_radius=6)
    WIN.blit(FONT.render(f"{player.mana}", True, TEXT), (p_hp_x+p_hp_w+8, p_hp_y+32))
    # messages box center-top
    pygame.draw.rect(WIN, (8,10,14,200), (24, 120, W-48-360, 90), border_radius=8)
    y = 126
    for msg in messages[-4:]:
        txt = FONT.render(msg, True, TEXT)
        WIN.blit(txt, (36, y)); y+=22
    # draw hand (cards surfaces passed in)
    start_x = 200
    gap = 18
    x = start_x
    for i, surf in enumerate(hand_surfaces):
        posy = HAND_Y
        sx = x + i*(CARD_W + gap)
        WIN.blit(surf, (sx, posy))
    # instruction
    ins = FONT.render("Click a card to play it (if enough mana). Press R to reset. Enter to next stage if win.", True, (180,180,200))
    WIN.blit(ins, (24, H-36))

#Main Game
def campaign_loop():
    # campaign progression
    step_idx = 0
    messages = ["Welcome to Neon Grid. Defeat the node!"]
    # initial stage
    stage = CAMPAIGN[step_idx]
    player = Player("Player", make_player_deck(), hp=10, mana=3)
    enemy = Player("Enemy", list(stage["enemy_deck"]), hp=10, mana=3)
    player.draw(5); enemy.draw(5)
    ai = AI(stage["ai"])
    round_no = 1
    selected_hand_idx = None
    won_stage = False
    t = 0
    hand_surfaces = []

    while True:
        dt = CLOCK.tick(FPS)
        t += dt
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_r:
                    # reset current stage
                    stage = CAMPAIGN[step_idx]
                    player = Player("Player", make_player_deck(), hp=10, mana=3)
                    enemy = Player("Enemy", list(stage["enemy_deck"]), hp=10, mana=3)
                    player.draw(5); enemy.draw(5)
                    ai = AI(stage["ai"])
                    messages.append("Stage reset.")
                    selected_hand_idx = None
                    won_stage = False
                if ev.key == pygame.K_RETURN and won_stage:
                    # next stage
                    step_idx = (step_idx+1) % len(CAMPAIGN)
                    stage = CAMPAIGN[step_idx]
                    player = Player("Player", make_player_deck(), hp=10, mana=3)
                    enemy = Player("Enemy", list(stage["enemy_deck"]), hp=10, mana=3)
                    player.draw(5); enemy.draw(5)
                    ai = AI(stage["ai"])
                    messages = [f"Entering: {stage['name']}"]
                    won_stage = False
                    selected_hand_idx = None
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx,my = pygame.mouse.get_pos()
                # detect hand clicks
                start_x = 200; gap=18
                clicked_idx = None
                for i in range(len(player.hand)):
                    sx = start_x + i*(CARD_W+gap); sy = HAND_Y
                    rect = pygame.Rect(sx,sy,CARD_W,CARD_H)
                    if rect.collidepoint(mx,my):
                        clicked_idx = i; break
                if clicked_idx is not None:
                    c = player.hand[clicked_idx]
                    if c.cost <= player.mana:
                        played = player.play_from_hand(clicked_idx)
                        player.mana -= played.cost
                        # when player plays, reset auto-boost flag (already reset in play_from_hand)
                        if sound_play:
                            try: sound_play.play()
                            except: pass
                        # enemy choose
                        enemy_choice_name = ai.choose(enemy, player, enemy.mana)
                        if enemy_choice_name is None:
                            possible = [x for x in list(enemy.deck)[:6] if CARD_TEMPLATES[x]["cost"] <= enemy.mana]
                            if possible:
                                enemy_choice_name = random.choice(possible)
                            else:
                                enemy_choice_name = random.choice(list(CARD_TEMPLATES.keys()))
                        enemy_choice_card = None
                        found = None
                        for j,cc in enumerate(enemy.hand):
                            if cc.key == enemy_choice_name and cc.cost <= enemy.mana:
                                found = j; break
                        if found is not None:
                            enemy_choice_card = enemy.play_from_hand(found)
                        else:
                            enemy_choice_card = Card(enemy_choice_name)
                        enemy.mana = max(0, enemy.mana - enemy_choice_card.cost)
                        # resolve
                        px = 200 + clicked_idx*(CARD_W+gap) + CARD_W//2
                        py = HAND_Y + CARD_H//2
                        ex = W-360 + 170; ey = 20 + 75
                        spawn_laser((px,py),(ex,ey))
                        msgs = resolve_round(played, enemy_choice_card, player, enemy)
                        messages.extend(msgs)
                        if enemy.hp < 10:
                            spawn_particles(ex, ey, PARTICLE, amount=20)
                        if player.hp < 10:
                            spawn_particles(px, py, (255,180,180), amount=14)
                        if sound_hit:
                            try: sound_hit.play()
                            except: pass
                        if enemy.hp <= 0:
                            messages.append("Node defeated! Stage cleared.")
                            if sound_win:
                                try: sound_win.play()
                                except: pass
                            won_stage = True
                        if player.hp <= 0:
                            messages.append("You were overwhelmed... Press R to retry.")
                        # end of round: both draw 1, mana regen +1
                        player.draw(1); enemy.draw(1)
                        player.mana = min(player.max_mana, player.mana+1)
                        enemy.mana = min(enemy.max_mana, enemy.mana+1)
                        round_no += 1
                    else:
                        messages.append("Not enough mana for that card.")
        # === NEW: auto-boost mana if no playable card in hand ===
        # If the player has no card with cost <= current mana, and we haven't auto-boosted yet,
        # give +1 mana (once) so the player can proceed.
        if not won_stage:
            playable = any(c.cost <= player.mana for c in player.hand)
            if not playable and not player._auto_mana_boosted:
                # only auto-boost if at least one card exists in hand (if hand empty, draw is attempted elsewhere)
                if player.hand:
                    player.mana = min(player.max_mana, player.mana + 1)
                    player._auto_mana_boosted = True
                    messages.append("No playable cards — auto +1 mana granted.")
        # background & visuals
        draw_neon_background(WIN, pygame.time.get_ticks())
        update_draw_lasers(WIN)
        update_particles(WIN)
        # pre-render hand surfaces
        hand_surfaces = []
        for i,c in enumerate(player.hand):
            sel = False
            s = render_card_surface(c, selected=sel)
            hand_surfaces.append(s)
        draw_ui(player, enemy, stage, messages, None, hand_surfaces, len(enemy.deck))
        # draw enemy avatar (simple neon cube)
        ex = W-360; ey = 20; ew = 340; eh = 150
        avx = ex + 170 + (enemy.shake_offset[0] if enemy.shake_offset else 0)
        avy = ey + 75 + (enemy.shake_offset[1] if enemy.shake_offset else 0)
        cube = pygame.Surface((120,120), pygame.SRCALPHA)
        pygame.draw.rect(cube, (20,28,40,200), (0,0,120,120), border_radius=10)
        pygame.draw.rect(cube, (*ACCENT,80), (8,8,104,104), border_radius=10)
        WIN.blit(cube, (avx-60, avy-60))
        WIN.blit(BIG.render("NODE", True, ACCENT_PINK), (avx-36, avy-8))
        # draw hand (with slight hover/offset)
        start_x = 200; gap=18
        for i,surf in enumerate(hand_surfaces):
            sx = start_x + i*(CARD_W+gap); sy = HAND_Y
            WIN.blit(surf, (sx,sy))
        if won_stage:
            win_text = BIG.render("STAGE CLEARED — Press Enter to continue", True, (160,255,200))
            WIN.blit(win_text, (W//2 - win_text.get_width()//2, H//2 - 20))
        fps = FONT.render(f"FPS: {int(CLOCK.get_fps())}", True, (180,220,255))
        WIN.blit(fps, (W-100, H-28))
        pygame.display.flip()

#Play
if __name__ == "__main__":
    campaign_loop()
