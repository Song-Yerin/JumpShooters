import pygame, sys, os, random, math, time
from pygame.locals import *
import pygame.mixer


WINDOW_SIZE = (960, 640) 
TILE_SIZE = 8                       # 타일 크기
TILE_MAPSIZE = (int(WINDOW_SIZE[0] / 7.5), int(WINDOW_SIZE[1] / 20))

DIR_PATH = os.path.dirname(__file__)    # 파일 위치
DIR_IMAGE = os.path.join(DIR_PATH, 'resources', 'image')
DIR_SOUND = os.path.join(DIR_PATH, 'resources','sound')
DIR_FONT = os.path.join(DIR_PATH, 'resources','font')

BACKGROUND_COLOR = (27, 25, 25)

DEFAULT_FONT_NAME = "munro.ttf"

floor_map = [-1] * TILE_MAPSIZE[0]     # 바닥 타일 맵(-1: 없음, 이외: y좌표)

objects = []                # 오브젝트 리스트
enemys = []                 # 적 오브젝트 리스트

# 스프라이트 시트 클래스 
class SpriteSheet:           
    def __init__(self, filename, width, height, max_row, max_col, max_index):
        baseImage = pygame.image.load(os.path.join(DIR_IMAGE, filename)).convert()
        self.spr = []
        self.width = width
        self.height = height

        for i in range(max_index):      # 스프라이트 시트의 각 인덱스에 자른 이미지 저장
            image = pygame.Surface((width, height))
            image.blit(baseImage, (0, 0), 
                       ((i % max_row) * width, (i // max_col) * height, width, height))
            image.set_colorkey((0, 0, 0))
            self.spr.append(image)

# 스프라이트 세트 생성 함수 
def createSpriteSet(spriteSheet, index_list, index_max = None):
    spr = []

    if index_max == None:
        for index in index_list:
            spr.append(spriteSheet.spr[index])
    else:
        for index in range(index_list, index_max + 1):
            spr.append(spriteSheet.spr[index])

    return spr

# 텍스트 드로우 함수
def draw_text(screen, text, size, color, x, y):
    gameFont = pygame.font.Font(resource_path(os.path.join(DIR_FONT, DEFAULT_FONT_NAME)), size)
    text_surface = gameFont.render(text, False, color)
    text_rect = text_surface.get_rect()
    text_rect.midtop = (round(x), round(y))
    screen.blit(text_surface, text_rect)

# 기본 오브젝트 클래스
class BaseObject:
    def __init__(self, spr, coord, kinds, game):
        self.kinds = kinds
        self.spr = spr
        self.spr_index = 0
        self.game = game
        self.width = spr[0].get_width()
        self.height = spr[0].get_height()
        self.direction = True
        self.vspeed = 0
        self.gravity = 0.2
        self.movement = [0, 0]
        self.collision = {'top' : False, 'bottom' : False, 'right' : False, 'left' : False}
        self.rect = pygame.rect.Rect(coord[0], coord[1], self.width, self.height)
        self.frameSpeed = 0
        self.frameTimer = 0
        self.destroy = False

    def physics(self):
        self.movement[0] = 0
        self.movement[1] = 0

        if self.gravity != 0:
            self.movement[1] += self.vspeed

            self.vspeed += self.gravity
            if self.vspeed > 3:
                self.vspeed = 3

    def physics_after(self):
        self.rect, self.collision = move(self.rect, self.movement)

        if self.collision['bottom']:
            self.vspeed = 0

        if self.rect.y > 700:
            self.destroy = True
    
    def draw(self):
        self.game.screen_scaled.blit(pygame.transform.flip(self.spr[self.spr_index], self.direction, False)
                    , (self.rect.x - self.game.camera_scroll[0], self.rect.y - self.game.camera_scroll[1]))

        if self.kinds == 'enemy' and self.hp < self.hpm:
            pygame.draw.rect(self.game.screen_scaled, (131, 133, 131)
            , [self.rect.x - 1 - self.game.camera_scroll[0], self.rect.y - 5 - self.game.camera_scroll[1], 10, 2])
            pygame.draw.rect(self.game.screen_scaled, (189, 76, 49)
            , [self.rect.x - 1 - self.game.camera_scroll[0], self.rect.y - 5 - self.game.camera_scroll[1], 10 * self.hp / self.hpm, 2])

    def animation(self, mode):
        if mode == 'loop':
            self.frameTimer += 1

            if self.frameTimer >= self.frameSpeed:
                self.frameTimer = 0
                if self.spr_index < len(self.spr) - 1:
                    self.spr_index += 1
                else:
                    self.spr_index = 0

    def destroy_self(self):
        if self.kinds == 'enemy':
            enemys.remove(self)

        objects.remove(self)
        del(self)

# 적 오브젝트 클래스
class EnemyObject(BaseObject):
    def __init__(self, spr, coord, kinds, game, types):
        super().__init__(spr, coord, kinds, game)
        self.types = types
        self.actSpeed = 0
        self.actTimer = 0
        self.hpm = 0
        self.hp = 0
        self.direction = False  # 이동 방향 초기화 (False: 오른쪽, True: 왼쪽)
        self.movement = [0, 0]  # x, y축 이동값
        
    def events(self):
        if self.hp < 1:
            self.destroy = True
            self.game.sound_monster.play()

            for i in range(4):
                coin = createObject(self.game.spr_coin, (self.rect.x + random.randrange(-3, 4), self.rect.y - 2), 'coin', self.game)
                coin.vspeed = random.randrange(-3, 0)
                coin.direction = random.choice([True, False])

        if not self.destroy:
            # Snake
            if self.types == 'snake':
                self.animation('loop')
                
            # 슬라임     
            elif self.types == 'slime': 
                self.animation('loop')
         

# 투사체 오브젝트 클래스
class EffectObject(BaseObject):
    def __init__(self, spr, coord, kinds, game, types):
        super().__init__(spr, coord, kinds, game)
        self.types = types
        self.lifetime = 0
        self.lifeTimer = 0
        self.damage = 0

    def events(self):
        self.physics()
        self.lifeTimer += 1

        if self.lifeTimer > self.lifetime:
            self.destroy = True

        if self.types == 'player_shot':       # 플레이어 공격일 경우
            self.animation('loop')

            if self.direction == False:
                self.movement[0] += 3
            else:
                self.movement[0] -= 3

            if self.collision['right'] or self.collision['left']:
                if self.direction:
                    self.direction = False
                    self.movement[0] += 4
                else:
                    self.direction = True
                    self.movement[0] -= 4

            for enemy in enemys:            # 적과 충돌 계산
                if self.destroy == False and enemy.destroy == False and self.rect.colliderect(enemy.rect):
                    self.destroy = True
                    enemy.hp -= self.damage

# 아이템 오브젝트 클래스
class ItemObject(BaseObject):
    def __init__(self, spr, coord, kinds, game, types):
        super().__init__(spr, coord, kinds, game)
        self.types = types

    def events(self):
        self.physics()
        self.animation('loop')

        if self.direction == False:
            self.movement[0] += 1
        else:
            self.movement[0] -= 1

        if self.collision['right'] or self.collision['left']:
            if self.direction:
                self.direction = False
                self.movement[0] += 2
            else:
                self.direction = True
                self.movement[0] -= 2

        if self.destroy == False and self.rect.colliderect(self.game.player_rect):
            self.destroy = True
            self.game.gameScore += 5
            self.game.sound_coin.play()


# 오브젝트 생성 함수
def createObject(spr, coord, types, game):
    if types == 'snake':
        obj = EnemyObject(spr, coord, 'enemy', game, types)
        obj.hpm = 50
        obj.hp = obj.hpm
        obj.frameSpeed = 4
    if types == 'slime':
        obj = EnemyObject(spr, coord, 'enemy', game, types)
        obj.hpm = 50
        obj.hp = obj.hpm
        obj.frameSpeed = 12
        obj.actSpeed = 120
        obj.actTimer = random.randrange(0, 120)
    if types == 'player_shot':
        obj = EffectObject(spr, coord, 'effect', game, types)
        obj.frameSpeed = 10
        obj.lifetime = 100
        obj.vspeed = -1
        obj.damage = 30
    if types == 'coin':
        obj = ItemObject(spr, coord, 'item', game, types)
        obj.frameSpeed = 25

    objects.append(obj)

    if obj.kinds == 'enemy':
        enemys.append(obj)

    return obj

# 바닥과 충돌 검사 함수
def collision_floor(rect):
    hit_list = []
    col = 0

    for row in floor_map:
        if row != -1:
            floor_rect = pygame.rect.Rect((col * TILE_SIZE, row * TILE_SIZE), (TILE_SIZE, TILE_SIZE * 5))
            if rect.colliderect(floor_rect):
                hit_list.append(floor_rect)
        col += 1

    return hit_list

# 오브젝트 이동 함수
def move(rect, movement):
    collision_types = {'top' : False, 'bottom' : False, 'right' : False, 'left' : False}    # 충돌 타입
    rect.x += movement[0]
    hit_list = collision_floor(rect)

    for tile in hit_list:           # X축 충돌 리스트 갱신
        if movement[0] > 0:
            rect.right = tile.left
            collision_types['right'] = True
        elif movement[0] < 0:
            rect.left = tile.right
            collision_types['left'] = True

    rect.y += movement[1]
    hit_list = collision_floor(rect)

    for tile in hit_list:           # Y축 충돌 리스트 갱신
        if movement[1] > 0:
            rect.bottom = tile.top
            collision_types['bottom'] = True
        elif movement[1] < 0:
            rect.top = tile.bottom
            collision_types['top'] = True

    return rect, collision_types

# 맵 이미지 생성 함수
def createMapImage(tileSpr, structSpr):
    image = pygame.Surface((TILE_MAPSIZE[0] * 8, TILE_MAPSIZE[1] * 8))
    front_image = pygame.Surface((TILE_MAPSIZE[0] * 8, TILE_MAPSIZE[1] * 8))
    empty = True                        # 빈칸
    case = 0                            # 타일 타입
    spr_index, spr_index2 = 0, []       # 타일 스프라이트 인덱스
    back_height = 0
    pattern_back = 0
    pattern_0 = 0

    for col in range(TILE_MAPSIZE[0] - 1):
        if floor_map[col] == -1:     # 비었을 경우
            empty = True
        else:                        # 타일이 존재할 경우
            if floor_map[col + 1] == -1:     # 앞 공간이 비었을 경우
                case = 2
                spr_index, spr_index2 = 4 + random.choice([0, 2]), [15, 16, 10]
            else:                           # 앞 공간에 타일이 존재할 경우
                if empty == True:                   # 이전 공간이 비었을 경우
                    case = 1
                    back_height = floor_map[col]
                    spr_index, spr_index2 = 3 + random.choice([0, 2]), [12, 13, 9]
                else:                               # 이전 공간에 타일이 존재할 경우
                    if floor_map[col - 1] > floor_map[col]:
                        case = 3
                        spr_index, spr_index2 = 3 + random.choice([0, 2]), [7]
                    else:
                        if floor_map[col + 1] == floor_map[col]:
                            case = 0
                            spr_index = pattern_0
                            pattern_0 += 1

                            if pattern_0 > 2:
                                pattern_0 = 0
                        else:
                            case = 4
                            spr_index, spr_index2 = 4 + random.choice([0, 2]), [8]
            empty = False

            for backtile in range(5 + back_height - floor_map[col]):        # 타일 뒷부분 채우기
                if backtile < 5:
                    image.blit(tileSpr.spr[29 - 3 * backtile + pattern_back], (col * TILE_SIZE
                        , (floor_map[col] - backtile + back_height - floor_map[col] + 4) * TILE_SIZE))
                else:
                    image.blit(tileSpr.spr[17 + pattern_back], (col * TILE_SIZE
                        , floor_map[col] * TILE_SIZE))
            pattern_back += 1

            if pattern_back > 2:
                pattern_back = 0

            image.blit(tileSpr.spr[spr_index], (col * TILE_SIZE, floor_map[col] * TILE_SIZE))   # 타일 앞부분 채우기

            if case != 0:
                i = 0
                for spr_indexs in spr_index2:
                    i += 1
                    image.blit(tileSpr.spr[spr_indexs], (col * TILE_SIZE, (floor_map[col] + i) * TILE_SIZE))

            # 구조물 채우기
            if random.randrange(0, 100) <= 4 and case == 0:
                if random.choice([True, False]):
                    image.blit(tileSpr.spr[32], ((col) * TILE_SIZE, (floor_map[col] - 1) * TILE_SIZE))
                else:
                    image.blit(tileSpr.spr[35], ((col - 1) * TILE_SIZE, (floor_map[col] - 2) * TILE_SIZE))
                    image.blit(tileSpr.spr[36], ((col) * TILE_SIZE, (floor_map[col] - 2) * TILE_SIZE))
                    image.blit(tileSpr.spr[37], ((col - 1) * TILE_SIZE, (floor_map[col] - 1) * TILE_SIZE))
                    image.blit(tileSpr.spr[38], ((col) * TILE_SIZE, (floor_map[col] - 1) * TILE_SIZE))

            if random.randrange(0, 100) <= 14:
                struct_types = random.choice(['leaf', 'flower', 'obj', 'sign', 'gravestone', 'skull'])
                struct_index = random.randrange(structSpr[struct_types][0], structSpr[struct_types][1])
                front_image.blit( tileSpr.spr[struct_index], (col * TILE_SIZE, (floor_map[col] - 1) * TILE_SIZE))

            if random.choice([True, False]):
                struct_index = random.randrange(47, 55)
                front_image.blit(tileSpr.spr[struct_index], (col * TILE_SIZE, (floor_map[col] - 1) * TILE_SIZE)) 

    image.set_colorkey((0, 0, 0))
    front_image.set_colorkey((0, 0, 0))

    return image, front_image


# 애니메이션 행동 변경 함수
def change_playerAction(frame, action_var, new_var, frameSpd, new_frameSpd, aniMode, new_aniMode):
    if action_var != new_var:
        action_var = new_var
        frame = 0
        frameSpd = new_frameSpd
        aniMode = new_aniMode

    return frame, action_var, frameSpd, aniMode

def resource_path(relative_path):
    """ PyInstaller 빌드된 파일과 개발 환경 모두에서 올바른 경로로 접근하게 해주는 함수 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def checkCollision(rect, map_data, tile_size):
        collisions = {'top': False, 'bottom': False, 'left': False, 'right': False}
    
        for y, row in enumerate(map_data):
            for x, tile in enumerate(row):
                if tile == 1:  # 장애물 타일만 검사
                    tile_rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
                    if rect.colliderect(tile_rect):  # AABB 충돌 체크
                        if rect.bottom > tile_rect.top and rect.top < tile_rect.top:
                            collisions['bottom'] = True
                        if rect.top < tile_rect.bottom and rect.bottom > tile_rect.bottom:
                            collisions['top'] = True
                        if rect.right > tile_rect.left and rect.left < tile_rect.left:
                            collisions['right'] = True
                        if rect.left < tile_rect.right and rect.right > tile_rect.right:
                            collisions['left'] = True
        return collisions


def move2(rect, movement, map_data, tile_size):
        collisions = {'top': False, 'bottom': False, 'left': False, 'right': False}
    
        rect.x += movement[0]
        x_collisions = checkCollision(rect, map_data, tile_size)
        if x_collisions['left'] or x_collisions['right']:  # x축 충돌이 있다면
            collisions.update(x_collisions)
            if movement[0] > 0:  # 오른쪽 이동 충돌
                rect.right = (rect.right // tile_size) * tile_size
            elif movement[0] < 0:  # 왼쪽 이동 충돌
                rect.left = (rect.left // tile_size + 1) * tile_size

        rect.y += movement[1]
        y_collisions = checkCollision(rect, map_data, tile_size)
        if y_collisions['top'] or y_collisions['bottom']:  # y축 충돌이 있다면
            collisions.update(y_collisions)
            if movement[1] > 0:  # 아래쪽 이동 충돌
                rect.bottom = (rect.bottom // tile_size) * tile_size
            elif movement[1] < 0:  # 위쪽 이동 충돌
                rect.top = (rect.top // tile_size + 1) * tile_size

        return rect, collisions  # 이동한 직사각형과 충돌 정보를 반환



# 게임 클래스
class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        
        WINDOW_SIZE = (960, 640)    

        # 게임 화면 설정
        pygame.display.set_caption('Mygame')                                      # 창 이름 설정
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode(WINDOW_SIZE, 0, 32)
        self.screen_scaled = pygame.Surface((WINDOW_SIZE[0] / 4, WINDOW_SIZE[1] / 4))        # 확대한 스크린
        
        
        self.show_start_screen()        # 시작 화면 표시

        self.camera_scroll = [TILE_MAPSIZE[0] * 4, 0]              # 카메라 이동 좌표

        self.gameScore = 0        # 점수
        self.GoalScore = 30       # 목표점수
        self.start_time = None    # 게임 시작 시간 설정
        self.timer_active = True  # 타이머 활성화

        # 리소스 불러오기
        self.spriteSheet_player = SpriteSheet('spriteSheet1.png', 16, 16, 8, 8, 12)      # 플레이어 스프라이트 시트
        self.spriteSheet_object = SpriteSheet('spriteSheet2.png', 8, 8, 16, 16, 45)      # 공통 오브젝트 스프라이트 시트
        self.spriteSheet_map1 = SpriteSheet('spriteSheet3.png', 8, 8, 16, 16, 87)         # 지형 2 스프라이트 시트

        self.spr_player = {}     # 플레이어 스프라이트 세트
        self.spr_player['stay'] = createSpriteSet(self.spriteSheet_player, [0])
        self.spr_player['run'] = createSpriteSet(self.spriteSheet_player, 1, 8)
        self.spr_player['jump'] = createSpriteSet(self.spriteSheet_player, [9, 10, 11])

        self.spr_effect = {}     # 효과 스프라이트 세트
        self.spr_effect['player_shot'] = createSpriteSet(self.spriteSheet_object, 37, 40)          
        self.spr_effect['player_shotBoom'] = createSpriteSet(self.spriteSheet_object, 41, 44)

        self.spr_enemy = {}      # 적 스프라이트 세트
        self.spr_enemy['slime'] = createSpriteSet(self.spriteSheet_map1, 81, 83)          
        self.spr_enemy['snake'] = createSpriteSet(self.spriteSheet_map1, 84, 86)

        self.spr_coin = createSpriteSet(self.spriteSheet_object, [41, 42])    # 코인 스프라이트 세트


        # 맵 데이터 및 스폰
        self.map_data, self.player_spon_x, self.player_spon_y, self.tile_positions = self.generateMap()   
       


        #효과음
        self.sound_attack = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'attack.wav'))
        self.sound_coin = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'coin.wav'))
        self.sound_footstep0 = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'footstep0.wav'))
        self.sound_footstep1 = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'footstep1.wav'))
        self.sound_monster = pygame.mixer.Sound(os.path.join(DIR_SOUND, 'monster.wav'))

           

        # 플레이어 컨트롤 변수
        self.keyLeft = False
        self.keyRight = False
        
        tile_size = 4

        self.player_rect = pygame.Rect((self.player_spon_x*tile_size, self.player_spon_y*tile_size ), (6, 14))
        self.player_movement = [0, 0]            # 플레이어 프레임당 속도
        self.player_vspeed = 0                   # 플레이어 y가속도
        self.player_flytime = 0                  # 공중에 뜬 시간   
        self.launching = True                    # 플레이어 바운스

        self.player_action = 'stay'              # 플레이어 현재 행동
        self.player_frame = 0                    # 플레이어 애니메이션 프레임
        self.player_frameSpeed = 1               # 플레이어 애니메이션 속도(낮을 수록 빠름. max 1)
        self.player_frameTimer = 0
        self.player_flip = False                 # 플레이어 이미지 반전 여부 (False: RIGHT)
        self.player_animationMode = True         # 애니메이션 모드 (False: 반복, True: 한번)
        self.player_walkSoundToggle = False
        self.player_walkSoundTimer = 0

        self.player_attack_timer = 0             # 플레이어 공격 타이머
        self.player_attack_speed = 15            # 플레이어 공격 속도

        # 배경음 실행
        pygame.mixer.music.load(os.path.join(DIR_SOUND, 'background.wav'))
        pygame.mixer.music.play(loops = -1)

        # 게임 실행
        self.run()

    def show_start_screen(self):
        start_clicked = False
        self.reset_enemy()
        while not start_clicked:
            self.screen.fill((0, 0, 0))  # 검은 배경
            
            # 게임 제목과 시작 버튼 텍스트 그리기
            draw_text(self.screen, "Jump Shooters", 72, (255, 255, 255), WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2 - 50)
            start_rect = pygame.Rect(WINDOW_SIZE[0] / 2 - 50, WINDOW_SIZE[1] / 2 + 50, 100, 50)

            mouse_pos = pygame.mouse.get_pos()
            if start_rect.collidepoint(mouse_pos):
                font_size = 48  
            else:
                font_size = 36  

            # "Start" 버튼 텍스트 그리기
            draw_text(self.screen, "Start", font_size, (255, 255, 255), WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2 + 50)
            
            # "Start" 버튼의 영역 설정
            start_rect = pygame.Rect(WINDOW_SIZE[0] / 2 - 50, WINDOW_SIZE[1] / 2 + 50, 100, 50)
            
            # 이벤트 처리
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if start_rect.collidepoint(event.pos):
                        start_clicked = True  # 시작 버튼 클릭 시 게임 시작
                        self.reset_enemy()

            pygame.display.update()
            self.clock.tick(60)

    def generateMap(self):
        map_data = []
        max_height = 100 # 맵의 높이 (행 수)
        max_width = 30  # 맵의 너비 (열 수)
        tile_positions = []  # 타일 위치를 저장할 리스트

        # 맵 초기화
        for y in range(max_height):
            row = []
            for x in range(max_width):
                if x == 0 or x == max_width - 1:  # 경계선 벽
                    row.append(1)
                    
                else:
                    row.append(0)
            map_data.append(row)

        # 고정 타일 데이터 생성
        fixed_tiles = [
            (2, 8, 10),   
            (18, 22, 10), 
            (11, 36, 7),   
            (3, 50, 11),   
            (18, 64, 10), 
            (4, 78, 9),   
        ]
        
        # 고정 타일 배치
        for (x_start, y, width) in fixed_tiles:
                for x in range(x_start, x_start + width):
                    if 0 < x < max_width - 1 and 0 <= y < max_height:
                        map_data[y][x] = 1
                        
                        top_y = y - 2  
                        if top_y >= 0 and (x, top_y) not in tile_positions:  # 중복 방지
                            tile_positions.append((x, top_y))
       
        tile_positions = self.unique_y_positions(tile_positions)

        spawn_x, spawn_y = 5, 0 

        return map_data, spawn_x+ 10, spawn_y, tile_positions
    
    def unique_y_positions(self,tile_positions):
        unique_tiles = {}
    
        # y 값 중복 제거, x 좌표가 가장 큰 값을 유지
        for x, y in tile_positions:
            if y not in unique_tiles:
                unique_tiles[y] = (x, y)
            else:
                if x > unique_tiles[y][0]:  # 더 큰 x 좌표가 있는 경우 업데이트
                    unique_tiles[y] = (x, y)
        print(unique_tiles.values())
        return list(unique_tiles.values())
    
    # 적 생성
    def spawnEnemies(self, tile_positions):  

        tile_size_y = random.choice([1, 4, 5, 7])
        randomNum = random.choice([ 50, 100, 150])

        selected_tiles = random.sample(tile_positions, 1)  
       
        # 적 위치가 지정된 범위 내에 있지 않을 때까지 반복
        while True:
            for tile_x, tile_y in selected_tiles:
                enemy_position = (tile_x + randomNum, (tile_y * tile_size_y) + randomNum - 2)
            
            if not (tile_x - 10 <= enemy_position[0] <= tile_x + 1 and tile_y -4 <= enemy_position[1] <= tile_y + 3):
                break  
        print(enemy_position)
        # 랜덤으로 'snake' 또는 'slime'을 선택하여 생성
        enemy_type = random.choice(['snake', 'slime'])
        if enemy_type == 'snake':
            createObject(self.spr_enemy['snake'], enemy_position, 'snake', self)
        else:
            createObject(self.spr_enemy['slime'], enemy_position, 'slime', self)


    def drawMap(self):
        # 맵의 타일 이미지 생성 및 캐싱
        if not hasattr(self, 'map_image'):
            self.map_image, self.front_image = createMapImage(self.spriteSheet_map1, self.spr_enemy)

        # 맵 이미지 화면에 그리기 (배경용)
        self.screen_scaled.blit(self.map_image, (-self.camera_scroll[0], -self.camera_scroll[1]))

        middle_tile_positions = []

        # 개별 타일 이미지 그리기
        tile_size = 8  # 타일 크기
        for y, row in enumerate(self.map_data):
            for x, tile in enumerate(row):
                if tile == 1:  # 장애물 타일일 경우
                                    
                    if x == 0:
                        base_image = self.spriteSheet_map1.spr[12]  # 베이스 이미지
                        overlay_image = self.spriteSheet_map1.spr[19]  # 3번 이미지
                        # 첫 번째 칸에 스프라이트 그리기
                        self.screen_scaled.blit(base_image, (x * tile_size - self.camera_scroll[0], y * tile_size - self.camera_scroll[1]))
                        self.screen_scaled.blit(overlay_image, (x * tile_size - self.camera_scroll[0], y * tile_size - self.camera_scroll[1]))

                    # 마지막 칸 (끝 타일)
                    elif x == len(row) - 1:
                        base_image = self.spriteSheet_map1.spr[15]  # 2번 이미지
                        overlay_image = self.spriteSheet_map1.spr[20]  # 4번 이미지
                        # 마지막 칸에 스프라이트 그리기
                        self.screen_scaled.blit(base_image, (x * tile_size - self.camera_scroll[0], y * tile_size - self.camera_scroll[1]))
                        self.screen_scaled.blit(overlay_image, (x * tile_size - self.camera_scroll[0], y * tile_size - self.camera_scroll[1]))

                    # 중간 칸 (중간 타일)
                    else:
                        base_image = self.spriteSheet_map1.spr[2]  # 1번 이미지
                        overlay_image = self.spriteSheet_map1.spr[19]  # 3번 이미지
                        # 중간 칸에 스프라이트 그리기
                        self.screen_scaled.blit(base_image, (x * tile_size - self.camera_scroll[0], y * tile_size - self.camera_scroll[1]))
                        self.screen_scaled.blit(overlay_image, (x * tile_size - self.camera_scroll[0], y * tile_size - self.camera_scroll[1]))
                        
                        middle_tile_positions.append((x, y))
    
    
    
    def launch_player(self):
        if self.launching:
            if self.player_flytime == 0:  
                self.player_vspeed -= 6.7

    
    def run(self):
         
        spawn_interval = 5  # 적 생성 간격 
        last_spawn_time = time.time()
        countdown = 150  # 카운트다운 시간 150초
        self.start_time = time.time()

        # 메인 루프
        while True:
            self.screen_scaled.fill(BACKGROUND_COLOR)            # 화면 초기화

            # 카메라 이동 설정
            self.camera_scroll[0] += int((self.player_rect.x - self.camera_scroll[0] - WINDOW_SIZE[0] / 8 - 5) / 16)
            self.camera_scroll[1] += int((self.player_rect.y - self.camera_scroll[1] - WINDOW_SIZE[1] / 8 - 2) / 16)

            
            self.launch_player()

            # 적 스폰
            if time.time() - last_spawn_time >= spawn_interval:
                self.spawnEnemies(self.tile_positions)
                last_spawn_time = time.time()

            # 남은 시간 계산
            if self.timer_active:
                elapsed_time = time.time() - self.start_time
                time_left = max(0, countdown - int(elapsed_time))

                # 타이머가 0이 되면 게임 오버 체크
                if time_left <= 0:
                    if self.gameScore < self.GoalScore:
                        self.show_game_over_screen()  # 점수가 20 미만이면 게임 오버 화면
                        return

                # 목표 점수 달성 시 게임 클리어 화면
                if self.gameScore >= self.GoalScore:
                    pygame.event.clear()
                    self.keyLeft = False
                    self.keyRight = False
                    self.show_game_clear_screen()
                    return

                # 화면 초기화 및 타이머 출력
                self.screen_scaled.fill(BACKGROUND_COLOR)
                draw_text(self.screen_scaled, f"Time Left: {time_left}", 18, (255, 255, 255), WINDOW_SIZE[0] / 8, 20)

            # 플레이어가 맵 밖으로 떨어졌는지 확인
            if self.player_rect.y > WINDOW_SIZE[1] + 50 : 
                self.show_game_over_screen()
                return

            
            if self.player_attack_timer < self.player_attack_speed:
                self.player_attack_timer += 1
            self.player_movement = [0, 0]                       # 플레이어 이동
            if self.keyLeft:
                self.player_movement[0] -= 2
            if self.keyRight:
                self.player_movement[0] += 2
            self.player_movement[1] += self.player_vspeed

            self.player_vspeed += 0.2
            if self.player_vspeed > 3:
                self.player_vspeed = 3

            if self.player_movement[0] != 0:                  # 플레이어 걷기 애니메이션 처리 및 방향 전환
                if self.player_flytime == 0:
                    self.player_frame, self.player_action, self.player_frameSpeed, self.player_animationMode = change_playerAction(
                        self.player_frame, self.player_action, 'run', self.player_frameSpeed, 3, self.player_animationMode, True)

                    self.player_walkSoundTimer += 1

                    if self.player_walkSoundTimer > 1:
                        self.player_walkSoundTimer = 0

                        if self.player_walkSoundToggle:
                            self.player_walkSoundToggle = False
                            self.sound_footstep0.play()
                        else:
                            self.player_walkSoundToggle = True
                            self.sound_footstep1.play()
                if self.player_movement[0] > 0:
                    self.player_flip = False
                else:
                    self.player_flip = True
            else:
                self.player_walkSoundTimer = 0

                if self.player_flytime == 0:
                    self.player_frame, self.player_action, self.player_frameSpeed, self.player_animationMode = change_playerAction(
                        self.player_frame, self.player_action, 'stay', self.player_frameSpeed, 3, self.player_animationMode, True)

            self.player_rect, player_collision = move2(self.player_rect, self.player_movement, self.map_data, 8)

            if player_collision['bottom']:
                self.player_vspeed = 0
                self.player_flytime = 0
            else:
                self.player_flytime += 1

            self.player_frameTimer += 1                          # 플레이어 애니메이션 타이머
            if self.player_frameTimer >= self.player_frameSpeed:
                self.player_frame +=1
                self.player_frameTimer = 0

                if self.player_frame >= len(self.spr_player[self.player_action]):
                    if self.player_animationMode == True:
                        self.player_frame = 0
                    else:
                        self.player_frame -= 1

            self.screen_scaled.blit(pygame.transform.flip(self.spr_player[self.player_action][self.player_frame], self.player_flip, False)
                               , (self.player_rect.x - self.camera_scroll[0] - 5, self.player_rect.y - self.camera_scroll[1] - 2))      # 플레이어 드로우

            for obj in objects:         # 오브젝트 이벤트 처리
                if obj.destroy:
                    obj.destroy_self()
                else:
                    obj.events()
                    obj.draw()
                    obj.physics_after()

            

            self.drawMap()
   
            draw_text(self.screen_scaled, f"Goal: {self.GoalScore}", 8, (238, 238, 230), 200, 130)
            
            draw_text(self.screen_scaled, "SCORE: " + str(self.gameScore), 8, (238, 238, 230), 200, 140)

            

            # 이벤트 컨트롤
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN:
                    if event.key == K_a:  # 왼쪽 이동
                        self.keyLeft = True
                    if event.key == K_d:  # 오른쪽 이동
                        self.keyRight = True
                    if event.key == K_w and self.player_flytime < 6:  # 점프
                        self.player_vspeed = -3.5
                        self.player_flytime += 1

                        self.player_frame, self.player_action, self.player_frameSpeed, self.player_animationMode = change_playerAction(
                            self.player_frame, self.player_action, 'jump', self.player_frameSpeed, 6, self.player_animationMode, False)
                    if event.key == K_SPACE and self.player_attack_timer >= self.player_attack_speed:  # 공격
                        self.player_attack_timer = 0
                        self.player_shot = createObject(self.spr_effect['player_shot'], (self.player_rect.x, self.player_rect.y + 2), 'player_shot', self)
                        self.player_shot.direction = self.player_flip
                        self.sound_attack.play()
                    
                if event.type == KEYUP:
                    if event.key == K_a:  # 왼쪽 이동 해제
                        self.keyLeft = False
                    if event.key == K_d:  # 오른쪽 이동 해제
                        self.keyRight = False

            surf = pygame.transform.scale(self.screen_scaled, WINDOW_SIZE)       # 창 배율 적용
            self.screen.blit(surf, (0, 0))

            pygame.display.update()
            self.clock.tick(60)



    def show_game_clear_screen(self):
        game_clear_clicked = False
        while not game_clear_clicked:
            self.screen.fill((0, 0, 0))  # 검은 배경
            
            # 게임 클리어 텍스트와 버튼 표시
            draw_text(self.screen, "Game Clear", 72, (0, 255, 0), WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2 - 50)
            draw_text(self.screen, "Home", 36, (255, 255, 255), WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2 + 50)
            draw_text(self.screen, "Continue", 36, (255, 255, 102), WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2 + 100)

            home_rect = pygame.Rect(WINDOW_SIZE[0] / 2 - 50, WINDOW_SIZE[1] / 2 + 50, 100, 50)
            continue_rect = pygame.Rect(WINDOW_SIZE[0] / 2 - 50, WINDOW_SIZE[1] / 2 + 100, 100, 50)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if home_rect.collidepoint(event.pos):
                        self.__init__()  # 홈으로 돌아가 초기화
                        return
                    elif continue_rect.collidepoint(event.pos):
                        self.timer_active = False  # 타이머 비활성화
                        game_clear_clicked = True  # 게임 계속하기
                        self.player_rect.x, self.player_rect.y = 30,10
                        


            pygame.display.update()
            self.clock.tick(60)

        self.run()

    def show_game_over_screen(self):
        game_over_clicked = False
        while not game_over_clicked:
            self.screen.fill((0, 0, 0))  # 검은 배경
            
            # 게임 오버 텍스트와 점수 표시
            draw_text(self.screen, "Game Over", 72, (255, 0, 0), WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2 - 50)
            draw_text(self.screen, f"Score: {self.gameScore}", 36, (255, 255, 255), WINDOW_SIZE[0] / 2, (WINDOW_SIZE[1] / 2) + 30)
            draw_text(self.screen, "ReStart", 36, (255, 255, 255), WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2 + 80)

            restart_rect = pygame.Rect(WINDOW_SIZE[0] / 2 - 50, WINDOW_SIZE[1] / 2 + 80, 100, 50)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if restart_rect.collidepoint(event.pos):
                        game_over_clicked = True  # "ReStart" 버튼 클릭 시 게임 재시작
                        self.__init__()  # 홈으로 돌아가 초기화
                        return
                       
                        
            pygame.display.update()
            self.clock.tick(60)



    

    def reset_enemy(self):
        for obj in objects:
                if obj.kinds == 'enemy':        
                    obj.destroy_self()
                    
        

        
game = Game()   # 게임 실행