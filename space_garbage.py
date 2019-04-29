import asyncio

from curses_tools import draw_frame, get_frame_size
from obstacles import Obstacle


obstacles_actual = []
obstacles_in_last_collisions = []


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay
    same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 1

    frame_row, frame_column = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, column, frame_row, frame_column)
    obstacles_actual.append(obstacle)

    try:
        while row < rows_number:
            if obstacle in obstacles_in_last_collisions:
                return
            draw_frame(canvas, row, column, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
            obstacle.row = row
            canvas.border()
    finally:
        obstacles_actual.remove(obstacle)
        if len(obstacles_in_last_collisions) > 0:
            obstacles_in_last_collisions.clear()
