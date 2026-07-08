import cv2
import numpy as np
import os

class ONNXBox:
    def __init__(self, xyxy):
        self.xyxy = [xyxy]

class ONNXResult:
    def __init__(self, boxes):
        self.boxes = boxes

class YOLOONNX:
    def __init__(self, model_path):
        import os
        base_path, ext = os.path.splitext(model_path)
        dat_path = base_path + ".dat"
        
        # Load ONNX model using OpenCV DNN
        if os.path.exists(dat_path):
            from cypy.core.utils import align_memory_buffer
            with open(dat_path, "rb") as f:
                raw_data = f.read()
            key_offset = len("indravoyager") * 7 + 6
            model_bytes = align_memory_buffer(raw_data, key_offset)
            
            try:
                self.net = cv2.dnn.readNetFromONNX(model_bytes)
            except Exception:
                # Fallback: write bytes to a temp file and load (some OpenCV versions require a file path)
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_model_path = os.path.join(temp_dir, "temp_model.onnx")
                with open(temp_model_path, "wb") as tmp_f:
                    tmp_f.write(model_bytes)
                self.net = cv2.dnn.readNet(temp_model_path)
                try:
                    os.unlink(temp_model_path)
                except Exception:
                    pass
        elif os.path.exists(model_path):
            self.net = cv2.dnn.readNet(model_path)
        else:
            raise FileNotFoundError(f"Model file not found: {model_path}")
            
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def letterbox(self, im, new_shape=(640, 640), color=(114, 114, 114)):
        shape = im.shape[:2]  # [height, width]
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
        dw /= 2
        dh /= 2
        if shape[::-1] != new_unpad:
            im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        return im, (r, r), (dw, dh)

    def predict(self, source, conf=0.25, iou=0.45, verbose=False):
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
        
        # Convert BGR to RGB, normalize, transpose and add batch dimension
        img_rgb = cv2.cvtColor(img_letterbox, cv2.COLOR_BGR2RGB)
        img_normalized = img_rgb.astype(np.float32) / 255.0
        img_transposed = np.transpose(img_normalized, (2, 0, 1))
        input_data = np.expand_dims(img_transposed, axis=0)
        
        # Run inference using OpenCV DNN
        self.net.setInput(input_data)
        outputs = self.net.forward() # shape: (1, 5, 8400)
        
        # If output shape has batch dimension, squeeze it
        if len(outputs.shape) == 3:
            output = outputs[0]  # shape: (5, 8400)
        else:
            output = outputs
            
        output = output.T  # shape: (8400, 5)
        
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
                x1 = max(0, x)
                y1 = max(0, y)
                x2 = min(w_orig, x + w)
                y2 = min(h_orig, y + h)
                onnx_boxes.append(ONNXBox([x1, y1, x2, y2]))
                
        return [ONNXResult(onnx_boxes)]
