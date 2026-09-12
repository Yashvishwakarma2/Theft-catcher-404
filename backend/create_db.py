import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('classes.db')
cursor = conn.cursor()

# Create table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS target_classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mode TEXT NOT NULL,
        class_name TEXT NOT NULL
    )
''')

# Clear existing data just in case
cursor.execute('DELETE FROM target_classes')

# Data to insert
database = {
    'person': ['person'],
    'mask': ['mask'],
    'weapon': ['knife', 'baseball ','cricket bat','gun','rifle','pistol','dagger','sword','mace','axe','hammer','chain','rope','brick','brick bat','chaku','kunta','kunta'],
    'object': [
        'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train',
    'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag',
    'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
    'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana',
    'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
    'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'dining table',
    'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock',
    'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
    ]
}

# Insert data
for mode, classes in database.items():
    for cls in classes:
        cursor.execute('INSERT INTO target_classes (mode, class_name) VALUES (?, ?)', (mode, cls))

# Commit and close
conn.commit()
conn.close()

print("Successfully created classes.db")
