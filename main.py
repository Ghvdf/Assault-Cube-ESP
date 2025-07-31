from pymem import Pymem
from tkinter import ttk
from tkinter import *
from helper import *
from ctypes import *
from pyray import *
import threading
import time
import math

class ESPApp:
    def __init__(self):
        self.running = True
        self.settings = {
            'show_lines': True,
            'line_cut_distance': 50,
            'show_rectangles': True,
            'show_names': True,
            'show_circles': True,
            'circles_radius': 10,
            'crosshair_circles_radius':1,
            'show_cut_circles': True,
            'hpBar' : True,
        }
        
        self.gui_thread = threading.Thread(target=self.create_gui, daemon=True)
        self.gui_thread.start()
        
        self.init_esp()
        self.run_esp()

    def create_gui(self):
        self.root = Tk()
        self.root.title("ESP Settings")
        self.root.geometry("400x400")
        
        # Переменные Tkinter
        self.var_lines = BooleanVar(value=self.settings['show_lines'])
        self.var_rectangles = BooleanVar(value=self.settings['show_rectangles'])
        self.var_names = BooleanVar(value=self.settings['show_names'])
        self.var_circles = BooleanVar(value=self.settings['show_circles'])
        self.var_cut_circles = BooleanVar(value=self.settings['show_cut_circles'])
        self.var_hpBar = BooleanVar(value=self.settings['hpBar'])
        
        # Флажки
        ttk.Checkbutton(self.root, text='Show Lines', variable=self.var_lines,
                       command=lambda: self.update_setting('show_lines', self.var_lines.get())).pack(anchor=W, padx=10, pady=5)
        ttk.Checkbutton(self.root, text='Show Rectangles', variable=self.var_rectangles,
                       command=lambda: self.update_setting('show_rectangles', self.var_rectangles.get())).pack(anchor=W, padx=10, pady=5)
        ttk.Checkbutton(self.root, text='Show Names', variable=self.var_names,
                       command=lambda: self.update_setting('show_names', self.var_names.get())).pack(anchor=W, padx=10, pady=5)
        ttk.Checkbutton(self.root, text='Show Circles', variable=self.var_circles,
                       command=lambda: self.update_setting('show_circles', self.var_circles.get())).pack(anchor=W, padx=10, pady=5)
        ttk.Checkbutton(self.root, text='Show Cut Circles', variable=self.var_cut_circles,
                       command=lambda: self.update_setting('show_cut_circles', self.var_cut_circles.get())).pack(anchor=W, padx=10, pady=5)
        ttk.Checkbutton(self.root, text='Hp Bar', variable=self.var_hpBar,
                       command=lambda: self.update_setting('hpBar', self.var_hpBar.get())).pack(anchor=W, padx=10, pady=5)
        
        # Слайдер для настройки обрезания линий
        ttk.Label(self.root, text="Line Cut Distance:").pack(anchor=W, padx=10, pady=(10,0))
        self.cut_scale = ttk.Scale(self.root, from_=0, to=200, 
                                  command=lambda v: self.update_setting('line_cut_distance', float(v)))
        self.cut_scale.set(self.settings['line_cut_distance'])
        self.cut_scale.pack(anchor=W, padx=10, pady=5, fill=X)

        # Слайдер для настройки радиуса окружности на голове
        ttk.Label(self.root, text="Circles_radius:").pack(anchor=W, padx=10, pady=(10,0))
        self.circles_radius = ttk.Scale(self.root, from_=1, to=100, 
                                  command=lambda v: self.update_setting('circles_radius', float(v)))
        self.circles_radius.set(self.settings['circles_radius'])
        self.circles_radius.pack(anchor=W, padx=10, pady=5, fill=X)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()
    
    def update_setting(self, key, value):
        self.settings[key] = value
    
    def init_esp(self):
        win = get_window_info("AssaultCube")
        set_trace_log_level(5)
        set_target_fps(60)
        set_config_flags(ConfigFlags.FLAG_WINDOW_UNDECORATED |
                        ConfigFlags.FLAG_WINDOW_MOUSE_PASSTHROUGH |
                        ConfigFlags.FLAG_WINDOW_TRANSPARENT |
                        ConfigFlags.FLAG_WINDOW_TOPMOST)
        init_window(win[2], win[3], "AssaultCube ESP")
        set_window_position(win[0], win[1])
        
        self.proc = Pymem("ac_client.exe")
        self.base = self.proc.base_address
    
    def draw_cut_line(self, start_x, start_y, end_x, end_y, color, cut_distance):
        # Вычисляем вектор направления
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx*dx + dy*dy)
        
        # Если линия слишком короткая, не рисуем
        if length <= cut_distance:
            return
        
        # Нормализуем вектор
        dx /= length
        dy /= length
        
        # Вычисляем новую начальную точку
        new_start_x = start_x + dx * cut_distance
        new_start_y = start_y + dy * cut_distance
        
        # Рисуем линию
        draw_line(int(new_start_x), int(new_start_y), int(end_x), int(end_y), color)
    
    def draw_cut_circles(self, cut_distance):
        if cut_distance <= 0:
            return
        
        center_x = get_screen_width() // 2
        center_y = get_screen_height() // 2
                
        draw_circle_lines(center_x, center_y, cut_distance, WHITE)

    
    def run_esp(self):
        while self.running and not window_should_close():
            try:
                matrix = self.proc.read_ctype(self.base + Pointer.view_matrix, (16 * c_float)())[:]
                player_count = self.proc.read_int(self.base + Pointer.player_count)

                begin_drawing()
                clear_background(BLANK)
                
                # Рисуем круги отрезания, если включено и cut_distance > 0
                if self.settings['show_cut_circles'] and self.settings['line_cut_distance'] > 0:
                    self.draw_cut_circles(self.settings['line_cut_distance'])
                
                if player_count > 1:
                    ents = self.proc.read_ctype(self.proc.read_int(self.base + Pointer.entity_list), 
                                             (player_count * c_int)())[1:]
                    for ent_addr in ents:
                        ent_obj = self.proc.read_ctype(ent_addr, Entity())
                        if ent_obj.health > 0:
                            try:
                                wts = world_to_screen(matrix, ent_obj.pos)
                                color = GREEN if ent_obj.team else RED

                                hpBarColor = GREEN if ent_obj.health else RED

                                if self.settings['show_rectangles']:
                                    draw_rectangle_lines(wts.x - 20, wts.y - 40, 40, ent_obj.health, color)

                                if self.settings['show_names']:
                                    draw_text(ent_obj.name, wts.x - measure_text(ent_obj.name, 12) // 2, 
                                            wts.y - 50, 12, WHITE)

                                if self.settings['show_circles']:
                                    draw_circle_lines(int(wts.x), int(wts.y), self.settings['circles_radius'], color)

                                if self.settings['show_lines']:
                                    center_x = get_screen_width() // 2
                                    center_y = get_screen_height() // 2
                                    self.draw_cut_line(center_x, center_y, wts.x, wts.y, color, 
                                                      self.settings['line_cut_distance'])
                                    
                                if self.settings['hpBar']:
                                    draw_rectangle(int(wts.x + 20), int(wts.y - 40), 5, ent_obj.health, hpBarColor)    

                            except Exception as e:
                                continue

                end_drawing()
            except Exception as e:
                print(f"ESP error: {e}")
                time.sleep(0.1)
    
    def on_close(self):
        self.running = False
        self.root.quit()
        close_window()

if __name__ == '__main__':
    app = ESPApp()