# подключаем нужные библиотеки
import cv2  # для работы с камерой и видео
import mediapipe as mp  # от гугла, ищет руки на видео
import time  # для задержек между кликами
import ctypes  # чтобы управлять мышью на windows

# настройки для управления мышью через windows
user32 = ctypes.windll.user32

def move_mouse(x, y):
    """перемещает курсор в нужную точку экрана"""
    user32.SetCursorPos(int(x), int(y))

def click_mouse():
    """делает один клик левой кнопкой мыши"""
    user32.mouse_event(2, 0, 0, 0, 0)  # нажимаем кнопку вниз
    time.sleep(0.05)  # маленькая пауза, чтобы компьютер понял
    user32.mouse_event(4, 0, 0, 0, 0)  # отпускаем кнопку

# настройки mediapipe для распознавания рук
mp_hands = mp.solutions.hands  # загружаем модель рук
mp_drawing = mp.solutions.drawing_utils  # инструмент для рисования точек
hands = mp_hands.Hands(
    min_detection_confidence=0.7,  # уверенность что это рука (0-1)
    min_tracking_confidence=0.5     # уверенность отслеживания движения
)

# узнаем размер экрана, чтобы двигать мышью по всему пространству
screen_w = user32.GetSystemMetrics(0)  # ширина экрана
screen_h = user32.GetSystemMetrics(1)  # высота экрана
print(f"размер экрана: {screen_w}x{screen_h}")

# открываем камеру
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # 0 - первая камера, dshow - драйвер для винды
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # уменьшаем разрешение для скорости
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# проверяем, получилось ли открыть камеру
if not cap.isOpened():
    print("камера не найдена!")
    exit()

print("программа запущена. esc - выход")
print("сведи большой и указательный палец для клика")

# переменные для плавного движения мыши
prev_x, prev_y = 0, 0  # предыдущие координаты пальца
smoothing = 3  # сглаживание (чем больше, тем плавнее но медленнее)
last_click_time = 0  # когда был последний клик
click_cooldown = 0.5  # полсекунды между кликами, чтобы не спамить

def get_distance(p1, p2):
    """считает расстояние между двумя точками на руке"""
    return ((p1.x - p2.x)**2 + (p1.y - p2.y)**2)**0.5

# главный бесконечный цикл программы
while True:
    # читаем один кадр с камеры
    ret, frame = cap.read()
    if not ret:
        print("ошибка кадра")
        break
    
    # отражаем по горизонтали, чтобы было как в зеркале
    frame = cv2.flip(frame, 1)
    
    # узнаем размеры текущего кадра
    frame_h, frame_w, _ = frame.shape
    
    # mediapipe работает с rgb, а opencv выдает bgr,所以要 конвертируем
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # запускаем распознавание рук на кадре
    result = hands.process(rgb)
    
    # если нашли хотя бы одну руку
    if result.multi_hand_landmarks:
        # проходим по каждой найденной руке
        for hand_landmarks in result.multi_hand_landmarks:
            # рисуем все точки и соединения между ними
            mp_drawing.draw_landmarks(
                frame, 
                hand_landmarks, 
                mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),  # зеленые точки
                mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)  # синие линии
            )
            
            # берем две важные точки: кончик указательного и большого пальца
            index_tip = hand_landmarks.landmark[8]   # указательный палец
            thumb_tip = hand_landmarks.landmark[4]   # большой палец
            
            # координаты указательного пальца на экране
            x = int(index_tip.x * frame_w)
            y = int(index_tip.y * frame_h)
            
            # плавное движение (не дергается)
            curr_x = prev_x + (x - prev_x) / smoothing
            curr_y = prev_y + (y - prev_y) / smoothing
            
            # переводим координаты с камеры на размер экрана
            screen_x = screen_w * (curr_x / frame_w)
            screen_y = screen_h * (curr_y / frame_h)
            
            # двигаем курсор мыши
            move_mouse(screen_x, screen_y)
            
            # запоминаем текущие координаты для следующего кадра
            prev_x, prev_y = curr_x, curr_y
            
            # проверяем жест "щипок" - большой и указательный вместе
            pinch_distance = get_distance(thumb_tip, index_tip)
            current_time = time.time()
            
            # если пальцы близко и прошло достаточно времени с прошлого клика
            if pinch_distance < 0.05 and (current_time - last_click_time) > click_cooldown:
                click_mouse()  # делаем клик
                last_click_time = current_time  # запоминаем время клика
                print("клик!")
            
            # подсвечиваем управляющую точку (указательный палец)
            cv2.circle(frame, (x, y), 15, (0, 0, 255), 3)   # красное кольцо
            cv2.circle(frame, (x, y), 10, (0, 0, 255), -1)  # красная заливка
            cv2.circle(frame, (x, y), 5, (255, 255, 255), -1)  # белый центр
            
            # если делаем клик - подсвечиваем еще и большой палец
            if pinch_distance < 0.05:
                thumb_x = int(thumb_tip.x * frame_w)
                thumb_y = int(thumb_tip.y * frame_h)
                cv2.circle(frame, (thumb_x, thumb_y), 15, (0, 255, 255), -1)  # желтый
    
    # показываем окно с видео
    cv2.imshow('hand tracking', frame)
    
    # ждем нажатия клавиши (1 миллисекунду)
    key = cv2.waitKey(1)
    
    # если нажали esc - выходим
    if key == 27:
        print("esc нажата")
        break
    # если нажали c - делаем тестовый клик (для проверки)
    elif key == ord('c') or key == ord('C'):
        click_mouse()
        print("тестовый клик")

# закрываем камеру и все окошки
cap.release()
cv2.destroyAllWindows()
hands.close()  # важно! освобождаем ресурсы mediapipe
print("программа завершена")