import asyncio
import curses
import itertools
import random
import time
from os.path import join

from fire_animation import fire
from curses_tools import draw_frame, get_frame_size, read_controls
from load_frames import load_frame_from_file, load_multiple_frames
from obstacles import show_obstacles
from physics import update_speed
from space_garbage import fly_garbage, obstacles_actual


TIC_TIMEOUT = 0.1
ANIM_DIR = 'anim_frames'
ROCKET_FRAMES_DIR = join(ANIM_DIR, 'rocket')
GARBAGE_FRAMES_DIR = join(ANIM_DIR, 'garbage')
GAME_OVER_FRAME = load_frame_from_file(
    join(ANIM_DIR, 'game_over', 'game_over.txt')
)


async def show_gameover(canvas, window_height, window_width, frame):
    message_size_y, message_size_x = get_frame_size(frame)
    message_pos_y = round(window_height / 2) - round(message_size_y / 2)
    message_pos_x = round(window_width / 2) - round(message_size_x / 2)
    while True:
        draw_frame(canvas, message_pos_y, message_pos_x, frame)
        await asyncio.sleep(0)


async def sleep(tics=1):
    iteration_count = int(tics * 10)
    for _ in range(iteration_count):
        await asyncio.sleep(0)


async def blink(canvas, row, column, symbol='*', offset=1):
    while True:
        if offset == 0:
            canvas.addstr(row, column, symbol, curses.A_DIM)
            await sleep(2)
            offset += 1

        if offset == 1:
            canvas.addstr(row, column, symbol)
            await sleep(0.3)
            offset += 1

        if offset == 2:
            canvas.addstr(row, column, symbol, curses.A_BOLD)
            await sleep(0.5)
            offset += 1

        if offset == 3:
            canvas.addstr(row, column, symbol)
            await sleep(0.3)
            offset = 0


def stars_generator(height, width, border_size, number_stars=50):
    for star in range(number_stars):
        y_pos = random.randint(border_size, height - border_size)
        x_pos = random.randint(border_size, width - border_size)
        symbol = random.choice(['+', '*', '.', ':'])
        yield y_pos, x_pos, symbol


async def animate_spaceship(canvas, frames, frame_container):
    frames_cycle = itertools.cycle(frames)

    while True:
        frame_container.clear()
        spaceship_frame = next(frames_cycle)
        frame_container.append(spaceship_frame)
        await asyncio.sleep(0)


async def run_spaceship(canvas, coros, row, col, frame_container, border_size):
    window_height, window_width = canvas.getmaxyx()

    symbol_size = 0

    frame_size_y, frame_size_x = get_frame_size(frame_container[0])

    frame_pos_x = round(col) - round(frame_size_x / 2)
    frame_pos_y = row

    row_speed, column_speed = 0, 0

    while True:

        direction_y, direction_x, spacebar = read_controls(canvas)

        if spacebar:
            shot_pos_x = frame_pos_x + round(frame_size_x / 2)
            shot_pos_y = frame_pos_y - symbol_size
            shot_coro = fire(canvas, shot_pos_y, shot_pos_x)
            coros.append(shot_coro)

        row_speed, column_speed = update_speed(
            row_speed,
            column_speed,
            direction_y,
            direction_x
        )

        frame_pos_x += column_speed
        frame_pos_y += row_speed

        frame_x_max = frame_pos_x + frame_size_x
        frame_y_max = frame_pos_y + frame_size_y

        field_x_max = window_width - border_size
        field_y_max = window_height - border_size

        frame_pos_x = min(frame_x_max, field_x_max) - frame_size_x
        frame_pos_y = min(frame_y_max, field_y_max) - frame_size_y

        frame_pos_x = max(frame_pos_x, border_size)
        frame_pos_y = max(frame_pos_y, border_size)

        current_frame = frame_container[0]

        draw_frame(canvas, frame_pos_y, frame_pos_x, current_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, frame_pos_y, frame_pos_x, current_frame, negative=True)

        for obstacle in obstacles_actual:
            if obstacle.has_collision(frame_pos_y, frame_pos_x):
                game_over_coro = show_gameover(
                    canvas,
                    window_height,
                    window_width,
                    GAME_OVER_FRAME
                )
                coros.append(game_over_coro)
                return


async def fill_orbit_with_garbage(canvas, coros, garbage_frames, border_size):
    _, columns_number = canvas.getmaxyx()

    while True:
        current_trash_frame = random.choice(garbage_frames)
        _, trash_column_size = get_frame_size(current_trash_frame)
        random_column = random.randint(
            border_size,
            columns_number - border_size
        )
        actual_column = min(
            columns_number - trash_column_size - border_size,
            random_column + trash_column_size - border_size,
        )

        trash_coro = fly_garbage(canvas, actual_column, current_trash_frame)
        coros.append(trash_coro)
        await sleep(2)


def run_event_loop(canvas, coroutines):
    while True:
        index = 0
        while index < len(coroutines):
            coro = coroutines[index]
            try:
                coro.send(None)
            except StopIteration:
                coroutines.remove(coro)
            index += 1
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


def main(canvas):
    frame_container = []
    curses.curs_set(False)
    canvas.border()
    border_size = 1
    canvas.nodelay(True)

    window_height, window_width = canvas.getmaxyx()

    coroutines = [
        blink(canvas, row, column, symbol, random.randint(0, 3))
        for row, column, symbol in stars_generator(
            window_height,
            window_width,
            border_size
        )
    ]

    garbage_frames = load_multiple_frames(GARBAGE_FRAMES_DIR)
    garbage_coro = fill_orbit_with_garbage(
        canvas,
        coroutines,
        garbage_frames,
        border_size
    )

    rocket_frames = load_multiple_frames(ROCKET_FRAMES_DIR)

    start_rocket_row = window_height
    start_rocket_col = window_width / 2

    rocket_anim_coro = animate_spaceship(
        canvas,
        rocket_frames,
        frame_container
    )
    rocket_control_coro = run_spaceship(
        canvas,
        coroutines,
        start_rocket_row,
        start_rocket_col,
        frame_container,
        border_size
    )

    show_obstacles_coro = show_obstacles(canvas, obstacles_actual)

    coroutines.append(rocket_anim_coro)
    coroutines.append(rocket_control_coro)
    coroutines.append(garbage_coro)
    coroutines.append(show_obstacles_coro)

    run_event_loop(canvas, coroutines)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(main)
