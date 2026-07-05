import cv2
import numpy as np
import onnxruntime

class ONNXBox:
    def __init__(self, xyxy):
        self.xyxy = [xyxy]

class ONNXResult:
    def __init__(self, boxes):
        self.boxes = boxes

class YOLOONNX:
    def __init__(self, model_path):
        # Disable verbose logging in ONNX Runtime
        opts = onnxruntime.SessionOptions()
        opts.log_severity_level = 3
        self.session = onnxruntime.InferenceSession(model_path, sess_options=opts)
        self.input_name = self.session.get_inputs()[0].name

    def letterbox(self, im, new_shape=(640, 640), color=(114, 114, 114)):
        # Resize and pad image while preserving aspect ratio
        shape = im.shape[:2]  # current shape [height, width]
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)

        # Scale ratio (new / old)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

        # Compute padding
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding

        dw /= 2  # divide padding into 2 sides
        dh /= 2

        if shape[::-1] != new_unpad:  # resize
            im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
        return im, (r, r), (dw, dh)

    def predict(self, source, conf=0.25, iou=0.45, verbose=False):
        # source can be a numpy array (BGR image) or path (string)
        if isinstance(source, str):
            img = cv2.imdecode(np.fromfile(source, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Could not read image from path: {source}")
        else:
            img = source.copy()
            
        h_orig, w_orig = img.shape[:2]
        
        # Preprocess using letterbox
        input_size = 640
        img_letterbox, ratio, (dw, dh) = self.letterbox(img, (input_size, input_size))
        
        img_rgb = cv2.cvtColor(img_letterbox, cv2.COLOR_BGR2RGB)
        img_normalized = img_rgb.astype(np.float32) / 255.0
        img_transposed = np.transpose(img_normalized, (2, 0, 1))
        input_data = np.expand_dims(img_transposed, axis=0)
        
        # Run inference
        outputs = self.session.run(None, {self.input_name: input_data})
        output = outputs[0][0] # shape (5, 8400)
        output = output.T # shape (8400, 5)
        
        boxes = []
        confidences = []
        
        for row in output:
            confidence = row[4]
            if confidence >= conf:
                xc, yc, w, h = row[:4]
                
                # Convert center to corners in 640x640 space
                x1 = xc - w/2
                y1 = yc - h/2
                
                # Convert from letterbox space back to original image space
                # 1. Subtract padding
                x1_scaled = (x1 - dw) / ratio[0]
                y1_scaled = (y1 - dh) / ratio[1]
                w_scaled = w / ratio[0]
                h_scaled = h / ratio[1]
                
                boxes.append([int(x1_scaled), int(y1_scaled), int(w_scaled), int(h_scaled)])
                confidences.append(float(confidence))
                
        # Apply NMS
        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf, iou)
        
        onnx_boxes = []
        if len(indices) > 0:
            flat_indices = np.array(indices).flatten()
            for idx in flat_indices:
                x, y, w, h = boxes[idx]
                # Make sure coordinates are within bounds
                x1 = max(0, x)
                y1 = max(0, y)
                x2 = min(w_orig, x + w)
                y2 = min(h_orig, y + h)
                onnx_boxes.append(ONNXBox([x1, y1, x2, y2]))
                
        return [ONNXResult(onnx_boxes)]
