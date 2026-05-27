# # #!/usr/bin/env python3
# # """
# # CAMS Bot — Control Node
# # Reads /joy topic and sends drive/turn commands to Pico over USB serial.

# # Serial protocol:
# #   D<float>,T<float>\n  — set velocity target and turn offset
# #   S\n                  — stop: zero velocity and turn
# #   K\n                  — kill switch
# #   R\n                  — resume from kill

# # Xbox button mapping:
# #   B (index 1) — kill
# #   A (index 0) — resume

# # Launch:
# #   ros2 run cams_bot control_node
# # """

# # import rclpy
# # from rclpy.node import Node
# # from sensor_msgs.msg import Joy
# # import serial


# # # PICO_PORT = '/dev/ttyPICO'
# # PICO_PORT = '/dev/ttyAMA3'
# # BAUD_RATE = 115200

# # # Axis indices from joystick_node
# # AXIS_DRIVE = 1   # left stick Y  — forward/back
# # AXIS_TURN  = 3   # right stick X — left/right

# # # Button indices (Xbox controller)
# # BTN_KILL   = 1   # B button — kill
# # BTN_RESUME = 0   # A button — resume

# # # Scaling
# # MAX_DRIVE  = 1.0   # max joystick drive value sent to Pico (Pico scales by DRIVE_SCALE)
# # MAX_TURN   = 0.3   # max turn differential

# # DEADZONE   = 0.1

# # # Ramping
# # DRIVE_RAMP = 0.1
# # TURN_RAMP  = 0.05


# # class ControlNode(Node):
# #     def __init__(self):
# #         super().__init__('cams_bot_control_node')

# #         try:
# #             self.ser = serial.Serial(PICO_PORT, BAUD_RATE, timeout=1, write_timeout=0)
# #             self.get_logger().info(f'Connected to Pico on {PICO_PORT}')
# #         except serial.SerialException as e:
# #             self.get_logger().error(f'Failed to open {PICO_PORT}: {e}')
# #             raise

# #         self.killed    = False
# #         self.last_cmd  = None
# #         self.cur_drive = 0.0
# #         self.cur_turn  = 0.0
# #         self.raw_drive = 0.0
# #         self.raw_turn  = 0.0

# #         self.sub = self.create_subscription(Joy, 'joy', self.joy_callback, 10)
# #         self.timer = self.create_timer(0.05, self.timer_callback)  # 20 Hz
# #         self.get_logger().info('CAMS Bot control node ready')

# #     def joy_callback(self, msg: Joy):
# #         # ── Kill ──────────────────────────────────────────────────────────────
# #         if msg.buttons[BTN_KILL]:
# #             if not self.killed:
# #                 self.killed    = True
# #                 self.cur_drive = 0.0
# #                 self.cur_turn  = 0.0
# #                 self.raw_drive = 0.0
# #                 self.raw_turn  = 0.0
# #                 self.last_cmd  = None
# #                 self._send('K')
# #                 self.get_logger().warn('KILLED')
# #             return

# #         # ── Resume ────────────────────────────────────────────────────────────
# #         if msg.buttons[BTN_RESUME]:
# #             if self.killed:
# #                 self.killed    = False
# #                 self.cur_drive = 0.0
# #                 self.cur_turn  = 0.0
# #                 self.raw_drive = 0.0
# #                 self.raw_turn  = 0.0
# #                 self.last_cmd  = None
# #                 self._send('R')
# #                 self.get_logger().info('RESUMED')
# #             return

# #         if self.killed:
# #             return

# #         # ── Store raw joystick values ─────────────────────────────────────────
# #         raw_drive = -msg.axes[AXIS_DRIVE]
# #         raw_turn  =  msg.axes[AXIS_TURN]

# #         self.raw_drive = 0.0 if abs(raw_drive) < DEADZONE else raw_drive * MAX_DRIVE
# #         self.raw_turn  = 0.0 if abs(raw_turn)  < DEADZONE else raw_turn  * MAX_TURN

# #     def timer_callback(self):
# #         if self.killed:
# #             return

# #         self.cur_drive = self._ramp(self.cur_drive, self.raw_drive, DRIVE_RAMP)
# #         self.cur_turn  = self._ramp(self.cur_turn,  self.raw_turn,  TURN_RAMP)

# #         if self.cur_drive == 0.0 and self.cur_turn == 0.0:
# #             if self.last_cmd != 'S':
# #                 self.last_cmd = 'S'
# #                 self._send('S')
# #             return

# #         cmd = f'D{self.cur_drive:.3f},T{self.cur_turn:.3f}'
# #         if cmd != self.last_cmd:
# #             self.last_cmd = cmd
# #             self._send(cmd)
# #             self.get_logger().info(f'Sent: {cmd}')

# #     def _ramp(self, current, target, step):
# #         diff = target - current
# #         if abs(diff) <= step:
# #             return target
# #         return current + step * (1 if diff > 0 else -1)

# #     def _send(self, cmd: str):
# #         try:
# #             self.ser.write(f'{cmd}\n'.encode())
# #         except serial.SerialTimeoutException:
# #             pass  # drop the command, don't block
# #         except serial.SerialException as e:
# #             self.get_logger().error(f'Serial write failed: {e}')

# #     def destroy_node(self):
# #         self.get_logger().info('Shutting down — sending kill to Pico')
# #         self._send('K')
# #         self.ser.close()
# #         super().destroy_node()


# # def main(args=None):
# #     rclpy.init(args=args)
# #     try:
# #         node = ControlNode()
# #         rclpy.spin(node)
# #     except KeyboardInterrupt:
# #         pass
# #     finally:
# #         rclpy.shutdown()


# # if __name__ == '__main__':
# #     main()

# #!/usr/bin/env python3
# """
# CAMS Bot — Control Node
# Reads /joy topic and sends drive/turn/boost commands to Pico over UART.

# Serial protocol:
#   D<float>,T<float>,B<float>\n  — drive, turn, boost
#   S\n                           — stop: zero all
#   K\n                           — kill switch
#   R\n                           — resume from kill

# Xbox button mapping:
#   B (index 1) — kill
#   A (index 0) — resume

# Launch:
#   ros2 run cams_bot control_node
# """

# import rclpy
# from rclpy.node import Node
# from sensor_msgs.msg import Joy
# import serial


# PICO_PORT = '/dev/ttyAMA3'
# BAUD_RATE = 115200

# # Axis indices
# AXIS_DRIVE = 1   # left stick Y  — forward/back
# AXIS_TURN  = 0   # left stick X  — left/right
# AXIS_BOOST = 5   # right trigger — speed boost

# # Button indices (Xbox controller)
# BTN_KILL   = 1   # B button — kill
# BTN_RESUME = 0   # A button — resume

# # Scaling
# MAX_DRIVE  = 1.0   # max joystick drive value sent to Pico
# MAX_TURN   = 0.3   # max turn differential

# DEADZONE   = 0.1

# # Ramping
# DRIVE_RAMP = 0.1
# TURN_RAMP  = 0.05


# class ControlNode(Node):
#     def __init__(self):
#         super().__init__('cams_bot_control_node')

#         try:
#             self.ser = serial.Serial(PICO_PORT, BAUD_RATE, timeout=1, write_timeout=0)
#             self.get_logger().info(f'Connected to Pico on {PICO_PORT}')
#         except serial.SerialException as e:
#             self.get_logger().error(f'Failed to open {PICO_PORT}: {e}')
#             raise

#         self.killed    = False
#         self.last_cmd  = None
#         self.cur_drive = 0.0
#         self.cur_turn  = 0.0
#         self.cur_boost = 0.0
#         self.raw_drive = 0.0
#         self.raw_turn  = 0.0
#         self.raw_boost = 0.0

#         self.sub = self.create_subscription(Joy, 'joy', self.joy_callback, 10)
#         self.timer = self.create_timer(0.05, self.timer_callback)  # 20 Hz
#         self.get_logger().info('CAMS Bot control node ready')

#     def joy_callback(self, msg: Joy):
#         # ── Kill ──────────────────────────────────────────────────────────────
#         if msg.buttons[BTN_KILL]:
#             if not self.killed:
#                 self.killed    = True
#                 self.cur_drive = 0.0
#                 self.cur_turn  = 0.0
#                 self.cur_boost = 0.0
#                 self.raw_drive = 0.0
#                 self.raw_turn  = 0.0
#                 self.raw_boost = 0.0
#                 self.last_cmd  = None
#                 self._send('K')
#                 self.get_logger().warn('KILLED')
#             return

#         # ── Resume ────────────────────────────────────────────────────────────
#         if msg.buttons[BTN_RESUME]:
#             if self.killed:
#                 self.killed    = False
#                 self.cur_drive = 0.0
#                 self.cur_turn  = 0.0
#                 self.cur_boost = 0.0
#                 self.raw_drive = 0.0
#                 self.raw_turn  = 0.0
#                 self.raw_boost = 0.0
#                 self.last_cmd  = None
#                 self._send('R')
#                 self.get_logger().info('RESUMED')
#             return

#         if self.killed:
#             return

#         # ── Store raw joystick values ─────────────────────────────────────────
#         raw_drive = -msg.axes[AXIS_DRIVE]
#         raw_turn  =  msg.axes[AXIS_TURN]

#         self.raw_drive = 0.0 if abs(raw_drive) < DEADZONE else raw_drive * MAX_DRIVE
#         self.raw_turn  = 0.0 if abs(raw_turn)  < DEADZONE else raw_turn  * MAX_TURN

#         # Right trigger: -1.0 (released) → 1.0 (pulled) → remap to 0.0–1.0
#         self.raw_boost = (msg.axes[AXIS_BOOST] + 1.0) / 2.0

#     def timer_callback(self):
#         if self.killed:
#             return

#         self.cur_drive = self._ramp(self.cur_drive, self.raw_drive, DRIVE_RAMP)
#         self.cur_turn  = self._ramp(self.cur_turn,  self.raw_turn,  TURN_RAMP)
#         self.cur_boost = self.raw_boost  # no ramp on trigger — instant response

#         if self.cur_drive == 0.0 and self.cur_turn == 0.0 and self.cur_boost == 0.0:
#             if self.last_cmd != 'S':
#                 self.last_cmd = 'S'
#                 self._send('S')
#             return

#         cmd = f'D{self.cur_drive:.3f},T{self.cur_turn:.3f},B{self.cur_boost:.3f}'
#         if cmd != self.last_cmd:
#             self.last_cmd = cmd
#             self._send(cmd)
#             self.get_logger().info(f'Sent: {cmd}')

#     def _ramp(self, current, target, step):
#         diff = target - current
#         if abs(diff) <= step:
#             return target
#         return current + step * (1 if diff > 0 else -1)

#     def _send(self, cmd: str):
#         try:
#             self.ser.write(f'{cmd}\n'.encode())
#         except serial.SerialTimeoutException:
#             pass  # drop the command, don't block
#         except serial.SerialException as e:
#             self.get_logger().error(f'Serial write failed: {e}')

#     def destroy_node(self):
#         self.get_logger().info('Shutting down — sending kill to Pico')
#         self._send('K')
#         self.ser.close()
#         super().destroy_node()


# def main(args=None):
#     rclpy.init(args=args)
#     try:
#         node = ControlNode()
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         rclpy.shutdown()


# if __name__ == '__main__':
#     main()

#!/usr/bin/env python3
"""
CAMS Bot — Control Node
Reads /joy topic and sends drive/turn/boost commands to Pico over UART.

Serial protocol:
  D<float>,T<float>,B<float>\n  — drive, turn, boost
  S\n                           — stop: zero all
  K\n                           — kill switch
  R\n                           — resume from kill

Xbox button mapping:
  B (index 1) — kill
  A (index 0) — resume

Launch:
  ros2 run cams_bot control_node
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import String
import serial


PICO_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

# Axis indices
AXIS_DRIVE = 1   # left stick Y  — forward/back
AXIS_TURN  = 2   # right stick X — left/right
AXIS_BOOST = 4   # right trigger — speed boost

# Button indices (Xbox controller)
BTN_KILL   = 1   # B button — kill
BTN_RESUME = 0   # A button — resume

# Scaling
MAX_DRIVE  = 1.0   # max joystick drive value sent to Pico
MAX_TURN   = 0.3   # max turn differential

DEADZONE   = 0.1

# Ramping — separate up and down rates
DRIVE_RAMP_UP   = 0.1    # fast push
DRIVE_RAMP_DOWN = 0.03   # gentle release
TURN_RAMP_UP    = 0.05
TURN_RAMP_DOWN  = 0.03


class ControlNode(Node):
    def __init__(self):
        super().__init__('cams_bot_control_node')

        try:
            self.ser = serial.Serial(PICO_PORT, BAUD_RATE, timeout=1, write_timeout=0)
            self.get_logger().info(f'Connected to Pico on {PICO_PORT}')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open {PICO_PORT}: {e}')
            raise

        self.killed    = False
        self.last_cmd  = None
        self.cur_drive = 0.0
        self.cur_turn  = 0.0
        self.cur_boost = 0.0
        self.raw_drive = 0.0
        self.raw_turn  = 0.0
        self.raw_boost = 0.0
        self.sub = self.create_subscription(Joy, 'joy', self.joy_callback, 10)
        # Subscribe to tracking node command messages
        self.cmd_sub = self.create_subscription(String, 'command', self.command_callback, 10)
        self.timer = self.create_timer(0.05, self.timer_callback)  # 20 Hz
        self.get_logger().info('CAMS Bot control node ready')

        # Tracking override state
        self.tracking_active = False
        self.tracked_D = 0.0
        self.tracked_T = 0.0
        self._last_tracking_time = None

    def joy_callback(self, msg: Joy):
        # ── Kill ──────────────────────────────────────────────────────────────
        if msg.buttons[BTN_KILL]:
            if not self.killed:
                self.killed    = True
                self.cur_drive = 0.0
                self.cur_turn  = 0.0
                self.cur_boost = 0.0
                self.raw_drive = 0.0
                self.raw_turn  = 0.0
                self.raw_boost = 0.0
                self.last_cmd  = None
                self._send('K')
                self.get_logger().warn('KILLED')
            return

        # ── Resume ────────────────────────────────────────────────────────────
        if msg.buttons[BTN_RESUME]:
            if self.killed:
                self.killed    = False
                self.cur_drive = 0.0
                self.cur_turn  = 0.0
                self.cur_boost = 0.0
                self.raw_drive = 0.0
                self.raw_turn  = 0.0
                self.raw_boost = 0.0
                self.last_cmd  = None
                self._send('R')
                self.get_logger().info('RESUMED')
            return

        if self.killed:
            return

        # ── Store raw joystick values ─────────────────────────────────────────
        raw_drive = -msg.axes[AXIS_DRIVE]
        raw_turn  =  msg.axes[AXIS_TURN]

        self.raw_drive = 0.0 if abs(raw_drive) < DEADZONE else raw_drive * MAX_DRIVE
        self.raw_turn  = 0.0 if abs(raw_turn)  < DEADZONE else raw_turn  * MAX_TURN

        # Right trigger: -1.0 (released) → 1.0 (pulled) → remap to 0.0–1.0
        self.raw_boost = (msg.axes[AXIS_BOOST] + 1.0) / 2.0

    def timer_callback(self):
        if self.killed:
            return

        self.cur_drive = self._ramp_asym(self.cur_drive, self.raw_drive,
                                          DRIVE_RAMP_UP, DRIVE_RAMP_DOWN)
        self.cur_turn  = self._ramp_asym(self.cur_turn, self.raw_turn,
                                          TURN_RAMP_UP, TURN_RAMP_DOWN)
        self.cur_boost = self.raw_boost  # no ramp on trigger — instant response

        # If recent tracking command exists, prefer it over joystick values.
        use_tracking = False
        if self._last_tracking_time is not None:
            age = (self.get_clock().now() - self._last_tracking_time).nanoseconds * 1e-9
            if age < 0.5 and self.tracking_active:
                use_tracking = True

        if use_tracking:
            # Map tracked D (0.0-2.0) to drive (0.0-1.0)
            drive_val = max(0.0, min(1.0, float(self.tracked_D) / 2.0))
            # Map tracked T (0.0-1.0) to scaled turn value
            turn_val = max(-MAX_TURN, min(MAX_TURN, float(self.tracked_T) * MAX_TURN))
            boost_val = 1.0
            cmd = f'D{drive_val:.3f},T{turn_val:.3f},B{boost_val:.3f}'
            if cmd != self.last_cmd:
                self.last_cmd = cmd
                self._send(cmd)
                self.get_logger().info(f'Tracking override sent: {cmd}')
            return

        if self.cur_drive == 0.0 and self.cur_turn == 0.0 and self.cur_boost == 0.0:
            if self.last_cmd != 'S':
                self.last_cmd = 'S'
                self._send('S')
            return
        cmd = f'D{self.cur_drive:.3f},T{self.cur_turn:.3f},B{self.cur_boost:.3f}'
        if cmd != self.last_cmd:
            self.last_cmd = cmd
            self._send(cmd)
            self.get_logger().info(f'Sent: {cmd}')

    def command_callback(self, msg: String):
        """Handle multiline command messages from `tracking_node`.

        Expected format (example):
        D = 0\nT = 0\nD = 2.0\nT = 0.3\ncommand = f"D{D},T{T},B1.0\n"
        We parse the last `D =` and `T =` lines and use those values.
        """
        try:
            data = msg.data.splitlines()
            d_val = None
            t_val = None
            # scan lines for the last explicit D = and T = values
            for line in data:
                line = line.strip()
                if line.startswith('D ='):
                    try:
                        d_val = float(line.split('=')[1].strip())
                    except Exception:
                        pass
                elif line.startswith('T ='):
                    try:
                        t_val = float(line.split('=')[1].strip())
                    except Exception:
                        pass

            if d_val is not None and t_val is not None:
                self.tracked_D = d_val
                self.tracked_T = t_val
                self.tracking_active = True
                self._last_tracking_time = self.get_clock().now()
                self.get_logger().debug(f'Received tracking D={d_val}, T={t_val}')
            else:
                # Couldn't parse — ignore but keep previous tracking state
                self.get_logger().warn('Received malformed tracking command')
        except Exception as e:
            self.get_logger().error(f'Failed to parse tracking command: {e}')

    def _ramp_asym(self, current, target, ramp_up, ramp_down):
        """Ramp with separate rates for increasing and decreasing magnitude."""
        diff = target - current
        if abs(diff) <= 0.001:
            return target
        # Picking ramp rate: if moving toward zero, use ramp_down; else ramp_up
        if abs(target) < abs(current):
            step = ramp_down
        else:
            step = ramp_up
        if abs(diff) <= step:
            return target
        return current + step * (1.0 if diff > 0 else -1.0)

    def _send(self, cmd: str):
        try:
            self.ser.write(f'{cmd}\n'.encode())
        except serial.SerialTimeoutException:
            pass  # drop the command, don't block
        except serial.SerialException as e:
            self.get_logger().error(f'Serial write failed: {e}')

    def destroy_node(self):
        self.get_logger().info('Shutting down — sending kill to Pico')
        self._send('K')
        self.ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = ControlNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()