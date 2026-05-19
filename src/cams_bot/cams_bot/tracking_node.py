#!/usr/bin/env python3
"""
Input Driver Node
Reads OAK-D tracking output and publishes to /joy topic
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
import depthai as dai


class JoystickNode(Node):
    def __init__(self):
        super().__init__('joystick_node')

        self.declare_parameter('publish_rate', 20.0)
        publish_rate = self.get_parameter('publish_rate').value

        self.publisher = self.create_publisher(Joy, 'joy', 10)
        self.timer = self.create_timer(1.0 / publish_rate, self.publish_joy)

        self._init_oakd()
        self.get_logger().info(f'Input node ready! mode=oakd @ {publish_rate} Hz')

    def _init_oakd(self):
        self.get_logger().info('Initializing OAK-D tracking input')
        OAKD_tracking(init=True)

    def publish_joy(self):
        axes = [0.0, 0.0, 0.0, 0.0]
        buttons = [0] * 8

        track = OAKD_tracking()
        if track is not None:
            x, y, z = track
            vx = max(-1.0, min(1.0, (1000.0 - z) / 1000.0))
            vy = max(-1.0, min(1.0, -x / 300.0))
            omega = max(-1.0, min(1.0, -x / 500.0))
            axes = [vy, -vx, 0.0, omega]

        msg = Joy()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'joystick'
        msg.axes = axes
        msg.buttons = buttons
        self.publisher.publish(msg)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def destroy_node(self):
        self.get_logger().info('Shutting down input node')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = JoystickNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error: {e}')
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()

def OAKD_tracking(init=False):
    if init or not hasattr(OAKD_tracking, '_initialized'):
        pipeline = dai.Pipeline()

        camRgb = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
        monoLeft = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
        monoRight = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)

        stereo = pipeline.create(dai.node.StereoDepth)
        leftOutput = monoLeft.requestOutput((640, 400))
        rightOutput = monoRight.requestOutput((640, 400))
        leftOutput.link(stereo.left)
        rightOutput.link(stereo.right)

        spatialDetectionNetwork = pipeline.create(dai.node.SpatialDetectionNetwork).build(camRgb, stereo, 'yolov6-nano')
        objectTracker = pipeline.create(dai.node.ObjectTracker)

        spatialDetectionNetwork.setConfidenceThreshold(0.6)
        spatialDetectionNetwork.input.setBlocking(False)
        spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
        spatialDetectionNetwork.setDepthLowerThreshold(100)
        spatialDetectionNetwork.setDepthUpperThreshold(5000)
        _ = spatialDetectionNetwork.getClasses()

        objectTracker.setDetectionLabelsToTrack([0])
        objectTracker.setTrackerType(dai.TrackerType.SHORT_TERM_IMAGELESS)
        objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)

        preview = objectTracker.passthroughTrackerFrame.createOutputQueue(maxSize=1, blocking=False)
        tracklets = objectTracker.out.createOutputQueue(maxSize=1, blocking=False)

        spatialDetectionNetwork.passthrough.link(objectTracker.inputTrackerFrame)
        spatialDetectionNetwork.passthrough.link(objectTracker.inputDetectionFrame)
        spatialDetectionNetwork.out.link(objectTracker.inputDetections)

        device = dai.Device(pipeline)
        OAKD_tracking._preview = preview
        OAKD_tracking._tracklets = tracklets
        OAKD_tracking._device = device
        OAKD_tracking._initialized = True
        return None

    preview = OAKD_tracking._preview
    tracklets = OAKD_tracking._tracklets
    imgFrame = preview.tryGet()
    track = tracklets.tryGet()
    if imgFrame is None or track is None:
        return None

    for t in track.tracklets:
        if t.id == 0:
            coords = t.spatialCoordinates
            return coords.x, coords.y, coords.z

    return None