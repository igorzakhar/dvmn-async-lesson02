import asyncio
import curses
from functools import partial
import itertools
import random
import time
from os.path import join

from fire_animation import fire
from curses_tools import draw_frame, get_frame_size, read_controls
from load_frames import load_frame_from_file, load_multiple_frames
from physics import update_speed
from space_garbage import fly_garbage, obstacles_actual


TIC_TIMEOUT = 0.1
ANIM_DIR = 'anim_frames'
ROCKET_FRAMES_DIR = join(ANIM_DIR, 'rocket')
GARBAGE_FRAMES_DIR = join(ANIM_DIR, 'garbage')
GAME_OVER_FRAME = load_frame_from_file(
    join(ANIM_DIR, 'game_over', 'game_over.txt')
)


async def count_years(year_counter, level_duration_sec=3, increment=5):
    while True:
        await sleep(level_duration_sec)
        year_counter[0] += increment


async def show_year_counter(canvas, year_counter, start_year):
    canvas_height, canvas_width = canvas.getmaxyx()

    counter_lenght = 9
    year_str_pos_y = 1
    year_str_pos_x = round(canvas_width / 2) - round(counter_lenght / 2)

    while True:
        current_year = start_year + year_counter[0]
        canvas.addstr(
            year_str_pos_y,
            year_str_pos_x,
            'Year {}'.format(current_year)
        )
        await asyncio.sleep(0)


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


def stars_generator(canvas, border_size, number_stars=50):
    height, width = canvas.getmaxyx()
    for star in range(number_stars):
        y_pos = random.randint(border_size, height - border_size - 1)
        x_pos = random.randint(border_size, width - border_size - 1)
        symbol = random.choice(['+', '*', '.', ':'])
        yield y_pos, x_pos, symbol


async def animate_spaceship(frames, frame_container):
    frames_cycle = itertools.cycle(frames)

    while True:
        frame_container.clear()
        spaceship_frame = next(frames_cycle)
        frame_container.append(spaceship_frame)
        await asyncio.sleep(0)


async def run_spaceship(
        canvas, coros, controls,
        frame_container, border_size, level, start_year):
    window_height, window_width = canvas.getmaxyx()
    start_rocket_row = window_height - border_size
    start_rocket_col = window_width / 2

    symbol_size = 0

    frame_size_y, frame_size_x = get_frame_size(frame_container[0])

    frame_pos_x = round(start_rocket_col) - round(frame_size_x / 2)
    frame_pos_y = start_rocket_row

    row_speed, column_speed = 0, 0

    while True:

        direction_y, direction_x, spacebar = controls()

        current_year = start_year + level[0]
        if current_year >= 2020 and spacebar:
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
        draw_frame(canvas, frame_pos_y, frame_pos_x,
                   current_frame, negative=True)

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


async def fill_orbit_with_garbage(
        canvas, coros, level, frames, border_size, timeout_minimal=0.3):
    _, columns_number = canvas.getmaxyx()

    while True:
        current_trash_frame = random.choice(frames)
        _, trash_column_size = get_frame_size(current_trash_frame)
        random_column = random.randint(
            border_size,
            columns_number - trash_column_size - border_size
        )

        trash_coro = fly_garbage(canvas, random_column, current_trash_frame)
        coros.append(trash_coro)

        garbage_respawn_timeout = calculate_respawn_timeout(level)

        if garbage_respawn_timeout <= timeout_minimal:
            garbage_respawn_timeout = timeout_minimal
        await sleep(garbage_respawn_timeout)


def calculate_respawn_timeout(level, initial_timeout=5, complexity_factor=20):
    timeout_step = level[0] / complexity_factor
    respawn_timeout = initial_timeout - timeout_step
    return respawn_timeout


def run_event_loop(screens, coroutines):
    while True:
        index = 0
        while index < len(coroutines):
            coro = coroutines[index]
            try:
                coro.send(None)
            except StopIteration:
                index = coroutines.index(coro)
                coroutines.remove(coro)
            else:
                index += 1
        for screen in screens:
            screen.refresh()
        time.sleep(TIC_TIMEOUT)


def main(canvas):
    frame_container = []
    start_year = 1957
    level = [0]
    curses.curs_set(False)
    canvas.nodelay(True)
    border_size = 1
    main_window_height, main_window_width = canvas.getmaxyx()

    status_bar_height = 2
    sb_begin_y = sb_begin_x = 0
    status_bar = canvas.derwin(
        status_bar_height,
        main_window_width,
        sb_begin_y,
        sb_begin_x
    )

    game_area_height = main_window_height - status_bar_height - border_size
    game_area_width = main_window_width
    ga_begin_y = status_bar_height + border_size
    ga_begin_x = 0
    game_area = canvas.derwin(
        game_area_height,
        game_area_width,
        ga_begin_y,
        ga_begin_x
    )
    game_area.border()

    coroutines = [
        blink(game_area, row, column, symbol, random.randint(0, 3))
        for row, column, symbol in stars_generator(game_area, border_size)
    ]

    garbage_frames = load_multiple_frames(GARBAGE_FRAMES_DIR)

    garbage_coro = fill_orbit_with_garbage(
        game_area,
        coroutines,
        level,
        garbage_frames,
        border_size
    )

    spaceship_controls = partial(read_controls, canvas=canvas)
    rocket_frames = load_multiple_frames(ROCKET_FRAMES_DIR)
    rocket_anim_coro = animate_spaceship(
        rocket_frames,
        frame_container
    )
    rocket_control_coro = run_spaceship(
        game_area,
        coroutines,
        spaceship_controls,
        frame_container,
        border_size,
        level,
        start_year
    )

    count_years_coro = count_years(level)
    show_year_counter_coro = show_year_counter(status_bar, level, start_year)

    coroutines.append(rocket_anim_coro)
    coroutines.append(rocket_control_coro)

    coroutines.append(garbage_coro)

    coroutines.append(count_years_coro)
    coroutines.append(show_year_counter_coro)

    screens = (canvas, game_area, status_bar)
    run_event_loop(screens, coroutines)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(main)
