import tkinter as tk
from tkinter import messagebox
from city_grid_streetlights import generate_grid_with_correct_streetlights, node_name

CELL_SIZE = 80
NODE_RADIUS = 10

class CityGridApp:
    def __init__(self, master, rows, cols):
        self.master = master
        self.master.title("🟢 City Grid Viewer")
        self.rows = rows
        self.cols = cols
        self.G, self.pos, self.streetlights = generate_grid_with_correct_streetlights(rows, cols)

        canvas_width = cols * CELL_SIZE + 100
        canvas_height = rows * CELL_SIZE + 100
        self.canvas = tk.Canvas(master, width=canvas_width, height=canvas_height, bg="white")
        self.canvas.pack()

        self.node_positions_gui = {}
        self.draw_grid()
        self.canvas.bind("<Button-1>", self.on_click)

    def draw_grid(self):
        for node, (x, y) in self.pos.items():
            x_gui = x * CELL_SIZE + 60
            y_gui = -y * CELL_SIZE + 60
            self.node_positions_gui[node] = (x_gui, y_gui)

            # Draw node
            self.canvas.create_oval(
                x_gui - NODE_RADIUS, y_gui - NODE_RADIUS,
                x_gui + NODE_RADIUS, y_gui + NODE_RADIUS,
                fill="lightblue", outline="black"
            )
            self.canvas.create_text(x_gui, y_gui - 15, text=node, font=("Arial", 8))

            # Draw edges
            for neighbor in self.G.successors(node):
                if neighbor in self.node_positions_gui:
                    continue  # already drawn from other side
                x2_gui, y2_gui = self.pos[neighbor]
                x2_gui = x2_gui * CELL_SIZE + 60
                y2_gui = -y2_gui * CELL_SIZE + 60

                edge = (node, neighbor)
                color = "black" if self.G[node][neighbor]['road_type'] == 'major' else "orange"
                self.canvas.create_line(x_gui, y_gui, x2_gui, y2_gui, fill=color, width=2, arrow=tk.LAST)

                # Optional: show small yellow dots for streetlights
                count = self.streetlights.get(edge, 0)
                for i in range(1, count + 1):
                    t = i / (count + 1)
                    xt = x_gui + t * (x2_gui - x_gui)
                    yt = y_gui + t * (y2_gui - y_gui)
                    self.canvas.create_oval(xt-2, yt-2, xt+2, yt+2, fill="yellow", outline="")

    def on_click(self, event):
        for node, (x, y) in self.node_positions_gui.items():
            if abs(event.x - x) < NODE_RADIUS + 4 and abs(event.y - y) < NODE_RADIUS + 4:
                self.show_node_info(node)
                return

    def show_node_info(self, node):
        info = f"📍 Node: {node}\n"
        data = self.G.nodes[node]
        info += f"Zone: {data['zone']}\n"
        info += f"Traffic Light: {'Yes' if data['traffic_light'] else 'No'}\n"
        if data['traffic_light']:
            info += f"Traffic Light Delay: {data['traffic_light_delay']}s\n"
        info += "\n🚗 Connected Roads:\n"

        for neighbor in self.G.successors(node):
            edge = self.G[node][neighbor]
            sl_count = self.streetlights.get((node, neighbor), 0)
            info += f"→ {neighbor}: {edge['road_type']} road, {edge['distance']} km, Capacity: {edge['capacity']}, Streetlights: {sl_count}\n"

        messagebox.showinfo(f"Details for {node}", info)

if __name__ == "__main__":
    root = tk.Tk()
    rows = 5 # you can change this
    cols = 5
    app = CityGridApp(root, rows, cols)
    root.mainloop()
