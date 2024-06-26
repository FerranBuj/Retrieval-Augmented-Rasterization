import time
import py5
import os
import glob
from pathlib import Path
from constants import(
        SIZE_W, SIZE_H,
        TILE_X, TILE_Y,
        TILE_W, TILE_H,
        MATRIX_X, MATRIX_Y,
        MATRIX_W, MATRIX_H,
        FRAMES, FILES,
        COLLECTION_NAME,
        OVERRIDE_ASPECT_RATIO,
        OUTPUT_PATH
)

from db_utils import get_chroma_client
from logutils import get_logger
logger = get_logger("main")
#due to the py5 library constraints
#variables initialized in settings and setup must be declared as globals
pg_frame_tiles = []
frame_matrices = []

collection = None
def settings():
    py5.size(120, 1, py5.P2D) #settings() allows passing variables to py.size() width and height.

def setup():
    global collection, client, render_pg, pg_frame_tiles, frame_matrices

    render_pg = py5.create_graphics(SIZE_W, SIZE_H)
    client = get_chroma_client()

    printer(f"\n-------------\n tiles_x:{TILE_X} tiles_y:{TILE_Y}\n matrix_x: {MATRIX_X} matrix_y: {MATRIX_Y} \n override_aspect_ratio: {OVERRIDE_ASPECT_RATIO}\n-------------")
    if(TILE_W < 1 or TILE_H <1 or MATRIX_W<1 or MATRIX_H<1):
        printer("SIZE VALUES ARE TOO SMALL")
        printer(f"tile_w: {TILE_W} tile_h: {TILE_H} matrix_w: {MATRIX_W} matrix_h: {MATRIX_H}")
        exit()
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME     
        )
        printer("Chroma collection found")
    except:
        printer("Chroma collection doesn't exist")
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hsnw:space":"l2"}  
        )
        printer("Initalizing files")
        initialize_file(FILES) #Initializes only one frame
        printer("Files successfully processed and stored")    

    printer("Initalizing frame")
    pg_frame_tiles, frame_matrices = initialize_frame(FRAMES[0], pg_frame_tiles, frame_matrices)
    printer("Frame successfully processed")


def draw():
    global frame_matrices, pg_frame_tiles, files_in_use
    files_in_use = set()
    pg = rasterize(render_pg)
    frame_name = f"{OUTPUT_PATH}/{SIZE_W}_{SIZE_H}_{TILE_X}_{TILE_Y}_{MATRIX_X}_{MATRIX_Y}_oar_{OVERRIDE_ASPECT_RATIO}_frame_count_{py5.frame_count}.png"
    pg.save(f"{os.path.join(frame_name)}")

    if py5.frame_count < len(FRAMES)-1:
        pg_frame_tiles = []
        frame_matrices = []
        printer("Initalizing frame")
        pg_frame_tiles, frame_matrices = initialize_frame(FRAMES[py5.frame_count], pg_frame_tiles, frame_matrices)
        printer("Frame successfully processed")
    else: 
        logger.info("Rasterization completed")
        py5.no_loop()
        exit()
    logger.info(f"{py5.frame_count}")

def printer(input): #py5 settings() setup() & draw() workaround
    logger.info(f"{input}")

def initialize_frame(frame, pg_frame_tiles, frame_matrices):
    frame = py5.load_image(frame)
    resize_pg = py5.create_graphics(SIZE_W, SIZE_H, py5.P2D)
    resize_pg.begin_draw()
    resize_pg.image(frame, 0, 0, SIZE_W, SIZE_H)
    resize_pg.end_draw()
    frame = resize_pg

    for y in range(0, SIZE_H, TILE_H):    
        for x in range(0, SIZE_W, TILE_W):
            tile = frame.get_pixels(int(x), int(y), TILE_W, TILE_H)
            temp_pg = py5.create_graphics(int(TILE_W), int(TILE_H), py5.P2D)
            temp_pg.begin_draw()
            temp_pg.image(tile, 0, 0, int(TILE_W), int(TILE_H))
            temp_pg.end_draw()
            pg_frame_tiles.append(temp_pg)
            frame_matrices = color_matrix(temp_pg, False, None, frame_matrices)
    return pg_frame_tiles, frame_matrices

def initialize_file(files): #pg_files_tiles):
    file_index = 0
    if OVERRIDE_ASPECT_RATIO:
        for file in files:
            file = py5.load_image(file)
            temp_pg = py5.create_graphics(TILE_W, TILE_H, py5.P2D)
            temp_pg.begin_draw()
            temp_pg.image(file, 0, 0, TILE_W, TILE_H)
            temp_pg.end_draw()
            #pg_files_tiles.append(temp_pg)
            color_matrix(temp_pg, True, file_index)
            file_index = file_index+1
            #return pg_files_tiles
    else:
        for file in files:
            file = py5.load_image(file)
            img_aspect_ratio = file.width / float(file.height)
            tile_aspect_ratio = TILE_W / float(TILE_H)

            if img_aspect_ratio > tile_aspect_ratio:
                scale_factor = TILE_W / float(file.width)
            else:
                scale_factor = TILE_H / float(file.height)
            
            scaled_width = int(file.width * scale_factor)
            scaled_height = int(file.height * scale_factor)
            temp_pg = py5.create_graphics(TILE_W, TILE_H, py5.P2D)
            temp_pg.begin_draw()
            temp_pg.image_mode(py5.CENTER)
            temp_pg.image(file, 0, 0, scaled_width, scaled_height)
            temp_pg.end_draw()
            #pg_files_tiles.append(temp_pg)
            color_matrix(temp_pg, True, file_index)
            file_index = file_index+1
            #return pg_files_tiles      
                      
def color_matrix(pg, store_matrices = False, index = None, matrices = None):
    matrix = [[0 for _ in range(4)] for _ in range(MATRIX_X * MATRIX_Y)]
    inner_index = 0
    for y in range(0, TILE_H, MATRIX_H):    
        for x in range(0, TILE_W, MATRIX_W):
            sum_a = sum_r = sum_g = sum_b = 0
            pg_matrix = pg.get_pixels(x, y, MATRIX_W, MATRIX_H)
            color_count = 0
            for pixel_y in range(MATRIX_H):
                for pixel_x in range(MATRIX_W):
                    c = pg_matrix.get_pixels(pixel_x, pixel_y)
                    
                    a = (c >> 24) & 0xFF #Check!
                    r = (c >> 16) & 0xFF
                    g = (c >> 8) & 0xFF
                    b = c & 0xFF

                    sum_a += a
                    sum_r += r
                    sum_g += g
                    sum_b += b
                    color_count += 1
            if color_count > 0:
                matrix[inner_index] = [
                    sum_r // color_count,
                    sum_g // color_count,
                    sum_b // color_count,
                    sum_a // color_count,
                ]
            #logger.info(f"subtile: {sub_tiles_index}, x: {x}, y: {y}, main color: {matrix[sub_tiles_index]}")
            if inner_index < (MATRIX_X * MATRIX_Y) - 1:
                inner_index += 1            
    if store_matrices:
        store_matrix(index, matrix)
    else:
        matrices.append(matrix)        
        return matrices
    
def euclidean_distance(frame_matrix): #for each frame tile, get the closest file tile.
    index = 0
    vector = []
    n_results = 5
    for rgba in frame_matrix: #matrix_x * matrix_y length
        vector.append(((rgba[0]<< 24) + (rgba[1] << 16) + (rgba[2] << 8) + (rgba[3])))         

    while True:  # Keep searching until an available index is found
        results = collection.query(
            query_embeddings=[vector],
            n_results=n_results,
            include=["distances"]  # ids are always returned
        )

        for index_list in results["ids"]:
            for index in index_list:
                if index not in files_in_use:
                    files_in_use.add(index)
                    return index
            
        # If no available index was found, increase the search scope
        if(n_results < len(FILES)):
            n_results += 50 #Performance trade-off?

def debug_setup(pg_frame_tiles):
    index = 0
    for y in range(0, SIZE_H, TILE_H):
        for x in range(0, SIZE_W, TILE_W):
            py5.push_matrix()
            py5.translate(x, y)
            py5.image(pg_frame_tiles[index], 0, 0, TILE_W, TILE_H)
            py5.pop_matrix()
            index = index+1

def store_matrix(index, matrix):
    logger.info(f"file matrix length: {len(matrix)}")
    vector = []
    for rgba in matrix: #matrix_x * matrix_y length
        vector.append((rgba[0]<< 24) + (rgba[1] << 16) + (rgba[2] << 8) + (rgba[3]))
    #convert each color array into an absolute value
    collection.add(
                embeddings = vector,
                ids=[f"{index}"]
                )
    logger.info("Matrix successfully stored")

def rasterize(pg):

    frame_index = 0
    for y in range(0, SIZE_H, TILE_H):
        for x in range(0, SIZE_W, TILE_W):

            index = euclidean_distance(frame_matrices[frame_index])
            logger.info(f"euclidean distance {index}")
            pg.begin_draw()
            pg.push_matrix()
            pg.translate(x, y)
            #Reload file image and place
            file = py5.load_image(FILES[int(index)])
            if OVERRIDE_ASPECT_RATIO:
                 pg.image(file, 0, 0, TILE_W, TILE_H)
            else:                 
                img_aspect_ratio = file.width / float(file.height)
                tile_aspect_ratio = TILE_W / float(TILE_H)
            
                if img_aspect_ratio > tile_aspect_ratio:
                    scale_factor = TILE_W / float(file.width)
                else:                    
                    scale_factor = TILE_H / float(file.height)

                scaled_width = int(file.width * scale_factor)
                scaled_height = int(file.height * scale_factor)
                pg.image_mode(py5.CENTER)
                pg.image(file, 0, 0, scaled_width, scaled_height)
            pg.pop_matrix()
            pg.end_draw()
            frame_index = frame_index+1

    return pg 


if __name__ == "__main__":
    py5.run_sketch()
    #gradio_interface.launch()