from email import message
import time
import arcade
import csv
import os 

# --- Константы ---
TILE_SCALING = 0.5
PLAYER_SCALING = 0.3

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Платформер"

SPRITE_PIXEL_SIZE = 128
GRID_PIXEL_SIZE = SPRITE_PIXEL_SIZE * TILE_SCALING

# Физика
MOVEMENT_SPEED = 5
JUMP_SPEED = 23
GRAVITY = 1.1

# Названия слоев из TileMap
LAYER_NAME_PLATFORMS = "Platforms"
LAYER_NAME_COINS = "Coins"
LAYER_NAME_BOMBS = "Bombs"


class PlayerCharacter(arcade.Sprite):
    """Анимированный персонаж."""

    def __init__(self):

        super().__init__()

        self.scale = PLAYER_SCALING

        # Текстуры
        self.idle_texture = arcade.load_texture("images/hero/bunny1_stand.png")
        self.walk1_texture = arcade.load_texture("images/hero/bunny1_walk1.png")
        self.walk2_texture = arcade.load_texture("images/hero/bunny1_walk2.png")
        self.jump_texture = arcade.load_texture("images/hero/bunny1_jump.png")

        # Начальная текстура
        self.texture = self.idle_texture

        # Счетчик анимации
        self.cur_texture = 0

        # Направление
        self.facing_right = True

    def update_animation(self, delta_time=1 / 60):

        # Поворот персонажа через scale_x
        if self.change_x < 0:
            self.facing_right = False
            self.scale_x = -PLAYER_SCALING

        elif self.change_x > 0:
            self.facing_right = True
            self.scale_x = PLAYER_SCALING

        # Прыжок
        if self.change_y != 0:
            self.texture = self.jump_texture
            return

        # Стоит
        if self.change_x == 0:
            self.texture = self.idle_texture
            return

        # Анимация ходьбы
        self.cur_texture += 1

        if self.cur_texture > 20:
            self.cur_texture = 0

        if self.cur_texture < 10:
            self.texture = self.walk1_texture
        else:
            self.texture = self.walk2_texture


class GameView(arcade.View):
    """Главный класс игрового экрана."""

    def __init__(self):
        """Инициализатор игрового вида."""
        super().__init__()

        # Объект нашей карты TileMap
        self.tile_map = None
        # Объект сцены (управляет всеми спрайтами)
        self.scene = None

        # Игрок и счет
        self.score = 0
        self.player_sprite = None

        self.physics_engine = None
        self.end_of_map = 0
        self.game_over = False

        # Переменные для FPS и времени
        self.last_time = None
        self.frame_count = 0

        # Камеры
        self.camera: arcade.Camera2D = None
        self.camera_shake = None

        # Звуки
        self.jump_sound = arcade.load_sound("sound/jump.mp3")

        # Таймер
        self.total_time = 120
        self.time_left = 120

        # Текстовые объекты
        self.text_fps = arcade.Text(
            "", x=10, y=40, color=arcade.color.BLACK, font_size=14
        )
        self.text_score = arcade.Text(
            f"Счет: {self.score}", x=10, y=20, color=arcade.color.BLACK, font_size=14
        )
        self.text_timer = arcade.Text(
            "02:00",
            x=WINDOW_WIDTH - 140,
            y=WINDOW_HEIGHT - 40,
            color=arcade.color.BLACK,
            font_size=24,
            bold=True,
        )

        # Проверка победы
        self.win = False

    def setup(self):
        """Настройка игры и инициализация переменных. Вызывайте для перезапуска."""

        # Путь к карте
        map_name = ":resources:tiled_maps/level_1.json"

        # Настройки слоев
        layer_options = {
            LAYER_NAME_PLATFORMS: {"use_spatial_hash": True},
            LAYER_NAME_COINS: {"use_spatial_hash": True},
            LAYER_NAME_BOMBS: {"use_spatial_hash": True},
        }

        # Загрузка карты
        self.tile_map = arcade.load_tilemap(map_name, TILE_SCALING, layer_options)
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

        # --- НАСТРОЙКА ИГРОКА ---
        self.player_sprite = PlayerCharacter()
        self.player_sprite.center_x = 196
        self.player_sprite.center_y = 128
        self.scene.add_sprite("Player", self.player_sprite)

        # Настройка камеры
        self.camera = arcade.Camera2D()
        self.camera_shake = arcade.camera.grips.ScreenShake2D(
            self.camera.view_data,
            max_amplitude=12.5,
            acceleration_duration=0.05,
            falloff_time=0.20,
            shake_frequency=15.0,
        )

        # Центрируем камеру на игроке
        self.pan_camera_to_user()

        # Рассчитываем конец карты
        self.end_of_map = self.tile_map.width * GRID_PIXEL_SIZE

        # Цвет фона из карты
        if self.tile_map.background_color:
            self.background_color = self.tile_map.background_color

        # Физический движок
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite,
            self.scene.get_sprite_list(LAYER_NAME_PLATFORMS),
            gravity_constant=GRAVITY,
        )

        self.game_over = False

    def on_resize(self, width, height):
        """Событие изменения размера окна."""
        super().on_resize(width, height)
        self.camera.match_window()

    def on_draw(self):
        """Отрисовка экрана."""
        self.clear()

        # Применяем эффекты тряски и активируем камеру игрового мира
        self.camera_shake.update_camera()
        with self.camera.activate():
            self.scene.draw()

        # Сбрасываем смещение тряски, чтобы оно не мешало логике слежения камеры
        self.camera_shake.readjust_camera()

        # Используем стандартную камеру (экранные координаты) для GUI
        with self.window.default_camera.activate():
            # Обновление текста FPS раз в 60 кадров
            if self.last_time and self.frame_count % 60 == 0:
                fps = 1.0 / (time.time() - self.last_time) * 60
                self.text_fps.text = f"FPS: {fps:5.2f}"

            if self.frame_count % 60 == 0:
                self.last_time = time.time()

            self.text_fps.draw()
            self.text_score.draw()
            self.text_timer.x = self.width - 140
            self.text_timer.y = self.height - 40
            self.text_timer.draw()

            if self.game_over:
                message = "ИГРА ОКОНЧЕНА"

                if self.win:
                    message = "ПОЗДРАВЛЯЮ!"

                arcade.draw_text(
                    message,
                    self.width / 2,
                    self.height / 2,
                    arcade.color.BLACK,
                    40,
                    anchor_x="center",
                )

        self.frame_count += 1

    def on_key_press(self, key, modifiers):
        """Вызывается при нажатии клавиши."""
        if key == arcade.key.UP or key == arcade.key.W:
            if self.physics_engine.can_jump():
                self.player_sprite.change_y = JUMP_SPEED
                arcade.play_sound(self.jump_sound)

        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.player_sprite.change_x = -MOVEMENT_SPEED
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.player_sprite.change_x = MOVEMENT_SPEED

    def on_key_release(self, key, modifiers):
        """Вызывается, когда пользователь отпускает клавишу."""
        if key in (arcade.key.LEFT, arcade.key.A, arcade.key.RIGHT, arcade.key.D):
            self.player_sprite.change_x = 0

    def pan_camera_to_user(self, panning_fraction: float = 1.0):
        """Плавное слежение камеры за персонажем."""
        screen_center_x, screen_center_y = self.player_sprite.position

        # Ограничение, чтобы камера не выходила за левый край
        if screen_center_x < self.camera.viewport_width / 2:
            screen_center_x = self.camera.viewport_width / 2
        # Ограничение для нижнего края
        if screen_center_y < self.camera.viewport_height / 2:
            screen_center_y = self.camera.viewport_height / 2

        user_centered = screen_center_x, screen_center_y

        self.camera.position = arcade.math.lerp_2d(
            self.camera.position,
            user_centered,
            panning_fraction,
        )
    def save_result(self):
        """Сохранение результата в CSV."""

        file_exists = os.path.exists("results.csv")

        elapsed = int(self.total_time - self.time_left)

        minutes = elapsed // 60
        seconds = elapsed % 60

        time_string = f"{minutes:02d}:{seconds:02d}"

        with open("results.csv", "a", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            # Заголовки
            if not file_exists:
                writer.writerow(["date", "time", "coins"])

            # Запись результата
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                time_string,
                self.score
            ])

    def on_update(self, delta_time):
        """Игровая логика и перемещение."""

        # Таймер
        if not self.game_over:
            self.time_left -= delta_time

        if self.time_left <= 0:
            self.time_left = 0
            self.game_over = True

        minutes = int(self.time_left) // 60
        seconds = int(self.time_left) % 60

        self.text_timer.text = f"{minutes:02d}:{seconds:02d}"

        if self.player_sprite.right >= self.end_of_map:
            self.game_over = True

        if not self.game_over:
            self.physics_engine.update()
            self.player_sprite.update_animation(delta_time)
            self.camera_shake.update(delta_time)

            # Сбор монет
            coins_hit = arcade.check_for_collision_with_list(
                self.player_sprite, self.scene.get_sprite_list(LAYER_NAME_COINS)
            )
            for coin in coins_hit:
                coin.remove_from_sprite_lists()
                self.score += 1
                if self.score >= 15:
                    self.win = True
                    self.game_over = True
                    self.save_result()

            # Столкновение с бомбами (активирует тряску)
            bombs_hit = arcade.check_for_collision_with_list(
                self.player_sprite, self.scene.get_sprite_list(LAYER_NAME_BOMBS)
            )
            for bomb in bombs_hit:
                bomb.remove_from_sprite_lists()
                self.camera_shake.start()

            # Обновляем положение камеры
            self.pan_camera_to_user(panning_fraction=0.12)
            self.text_score.text = f"Счет: {self.score}"


def main():
    """Основная функция запуска."""
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, resizable=True)
    game = GameView()
    game.setup()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
