import asyncio
import curses
import itertools
import random
import time
from os import listdir
from os.path import isfile, join

from fire_animation import fire
from curses_tools import draw_frame, get_frame_size, read_controls
from space_garbage import fly_garbage
from physics import update_speed


TIC_TIMEOUT = 0.1
ANIM_DIR = 'anim_frames'
ROCKET_FRAMES_DIR = join(ANIM_DIR, 'rocket')
GARBAGE_FRAMES_DIR = join(ANIM_DIR, 'garbage')
spaceship_frame = ''


def load_frame_from_file(filename):
    with open(filename, 'r') as fd:
        return fd.read()


def get_frames_list(dirnames):
    return [
        load_frame_from_file(join(dirnames, file))
        for file in listdir(dirnames)
        if isfile(join(dirnames, file))
    ]


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


def stars_generator(height, width, number=50):
    for star in range(number):
        y_pos = random.randint(1, height - 2)
        x_pos = random.randint(1, width - 2)
        symbol = random.choice(['+', '*', '.', ':'])
        yield y_pos, x_pos, symbol


async def animate_spaceship(canvas, frames):
    global spaceship_frame
    frames_cycle = itertools.cycle(frames)

    while True:
        spaceship_frame = next(frames_cycle)
        await sleep(0.3)


async def run_spaceship(canvas, start_row, start_column):
    height, width = canvas.getmaxyx()
    border_size = 1

    frame_size_y, frame_size_x = get_frame_size(spaceship_frame)
    frame_pos_x = round(start_column) - round(frame_size_x / 2)
    frame_pos_y = round(start_row) - round(frame_size_y / 2)

    row_speed = column_speed = 0

    while True:
        draw_frame(canvas, frame_pos_y, frame_pos_x,
                   spaceship_frame, negative=True)

        await sleep(0.3)

        direction_y, direction_x, _ = read_controls(canvas)

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

        field_x_max = width - border_size
        field_y_max = height - border_size

        frame_pos_x = min(frame_x_max, field_x_max) - frame_size_x
        frame_pos_y = min(frame_y_max, field_y_max) - frame_size_y
        frame_pos_x = max(frame_pos_x, border_size)
        frame_pos_y = max(frame_pos_y, border_size)

        draw_frame(canvas, frame_pos_y, frame_pos_x, spaceship_frame)
        canvas.refresh()


async def fill_orbit_with_garbage(canvas, coros, garbage_frames):
    _, columns_number = canvas.getmaxyx()
    border_size = 1
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


def run_event_loop(coroutines):
    while True:
        index = 0
        while index < len(coroutines):
            coro = coroutines[index]
            try:
                coro.send(None)
            except StopIteration:
                coroutines.remove(coro)
            index += 1

        time.sleep(TIC_TIMEOUT)


def main(canvas):
    curses.curs_set(False)
    canvas.border()
    canvas.nodelay(True)

    height, width = canvas.getmaxyx()

    coroutines = [
        blink(canvas, row, column, symbol, random.randint(0, 3))
        for row, column, symbol in stars_generator(height, width)
    ]

    start_row = height - 2
    start_col = width / 2
    coro_shot = fire(canvas, start_row, start_col)
    coroutines.append(coro_shot)

    garbage_frames = get_frames_list(GARBAGE_FRAMES_DIR)
    garbage_coro = fill_orbit_with_garbage(canvas, coroutines, garbage_frames)

    rocket_frames = get_frames_list(ROCKET_FRAMES_DIR)
    start_rocket_row = height / 2

    rocket_anim_coro = animate_spaceship(canvas, rocket_frames)
    rocket_control_coro = run_spaceship(canvas, start_rocket_row, start_col)

    coroutines.append(garbage_coro)
    coroutines.append(rocket_anim_coro)
    coroutines.append(rocket_control_coro)

    canvas.refresh()

    run_event_loop(coroutines)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(main)
