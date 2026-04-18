import cv2
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog 
from PIL import Image, ImageTk
import customtkinter as ctk
import sys

# Appearance
ctk.set_appearance_mode("dark") # Darkmode :)
ctk.set_default_color_theme("blue")

CORRECT_CODE = "123" # Program passcode
defaultCam = 0

class MotionMonitoring:
    def __init__(self, window):
        self.window = window
        self.window.title("Motion Monitoring") #title

        # Setting/resetting program default settings
        self.currentCam = defaultCam
        self.cap = None
        self.avg_background = None
        self.is_monitoring = False
        self.fps_delay = 33

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        # Can't access camera (error msg)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not access webmcam.")
            self.window.destroy()
            return

        self.setupUi()

        # Release camera when closed
        self.window.protocol("WM_DELETE_WINDOW", self.onClosing)

    def findCams(self): # Searching for existing webcams
        index = 0
        arr = [] # Creating an array to place the found cameras in
        for index in range(5): #max of 5 cams

            # Checking for both DSHOW and MSMF capture methods for higher compatibility between old/modern cameras
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(index, cv2.CAP_MSMF)

            # If found, -> read
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    arr.append(str(index))
                cap.release()
        return arr

    def changeCam(self, newIdx): # Change current -> next webcam
        newIdx = int(newIdx)

        # Check if current cam exists within index
        if hasattr(self, 'currentCam') and self.currentCam == newIdx:
            return

        self.currentCam = newIdx
        # Reset
        self.is_monitoring = False

        # Update/refresh Monitoring Toggle button (was stuck on as a bug between switching camera)
        if hasattr(self, 'monitor_btn'): self.monitor_btn.configure(text="Start Monitoring", fg_color="#1f538d", hover_color="#14385e")

        if self.cap and self.cap.isOpened():
            self.cap.release()

        # Placing new index in place of device #
        self.cap = cv2.VideoCapture(newIdx, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            messagebox.showerror("Error", f"Failed to connect to Camera {newIdx}") # Connection to camera error msg
            return
        
        self.avg_background = None
        print(f"Switched to new Source: {newIdx}") # Print success message

    def nextCam(self): # Next webcam option
        availableCams = self.findCams()

        # Error message if no camera detected
        if not availableCams:
            messagebox.showwarning("Warning", "No more cameras detected.")
            return
        
        # Check position in list of devices
        try:
            currentStr = str(self.currentCam)
            if currentStr in availableCams:
                currentPos = availableCams.index(currentStr)
                nextPos = (currentPos + 1) % len(availableCams)
                nextIdx = availableCams[nextPos]
            else:
                nextIdx = availableCams[0]

            self.changeCam(nextIdx)

        except Exception as e:
            print(f"Switch Error: {e}")
            self.changeCam(availableCams[0])

    def setupUi(self): # Framing and buttons
        # Feed Display
        self.video_label = ctk.CTkLabel(self.window, text = "", fg_color = "black")
        self.video_label.pack(padx=20, pady=20)

        # Adjustments
        self.control_frame = ctk.CTkFrame(self.window)
        self.control_frame.pack(padx=20, pady=20, fill="x")

        self.settings_label = ctk.CTkLabel(self.control_frame, text="ADJUSTMENTS", font=("Arial", 12, "bold"), text_color="#abb2bf")
        self.settings_label.pack(pady=(10, 5))

        # Resolution Adjustments
        self.res_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.res_frame.pack(pady=5)

        # Resolution Adjustments
        ctk.CTkButton(self.res_frame, text="480p", command = lambda: self.setRes(640, 480)).pack(side="left", padx=5)
        ctk.CTkButton(self.res_frame, text="720p", command = lambda: self.setRes(1280, 720)).pack(side="left", padx=5)
        
        # FPS Adjustments
        ctk.CTkButton(self.res_frame, text=" 5 FPS", command = lambda: self.setFps(5)).pack(side="left", padx=5)        
        ctk.CTkButton(self.res_frame, text="15 FPS", command = lambda: self.setFps(15)).pack(side="left", padx=5)
        ctk.CTkButton(self.res_frame, text="30 FPS", command = lambda: self.setFps(30)).pack(side="left", padx=5)

        # Monitor Toggle
        self.monitor_btn = ctk.CTkButton(self.res_frame, text="Begin Monitoring", fg_color="#1f538d", hover_color="#14375e", command=self.monitorToggle)
        self.monitor_btn.pack(side="right", padx=5)

        # Camera Choice
        ctk.CTkButton(self.res_frame, text="NEXT CAM ➔", command = self.nextCam).pack(side="left", padx=5)

    def setRes(self, w, h): # Resolution calculations
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self.avg_background = None
        print(f"Resolution set to {w}x{h}")

    def setFps(self, val): # Frames per second calculations
        self.fps_delay = int(1000/val)
        print(f"Delay set to: {self.fps_delay}ms")

    def monitorToggle(self): # Begin/stop monitoring/detecting motion in the feed
        self.is_monitoring = not self.is_monitoring
        # If monitoring = true, button shows "Stop"
        state = "Stop" if self.is_monitoring else "Start"
        self.monitor_btn.configure(text=f"{state} Monitoring")
        # Refresh background when new launch
        if self.is_monitoring:
            self.monitor_btn.configure(fg_color="#942a2a", hover_color="#6e1e1e")
            self.avg_background = None
        else:
            self.monitor_btn.configure(fg_color="#1f538d", hover_color="#14385e")

    def motionDetection(self, frame): # Motion detection algorithm & settings
        # Grayscaling and bluring
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (25, 15), 0)

        if self.avg_background is None:
            self.avg_background = gray.copy().astype("float")
            return frame, False
        
        # Smooth noise in lesser quality cameras
        cv2.accumulateWeighted(gray, self.avg_background, 0.25)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg_background))

        # Thresholding and dilating
        _, thresh = cv2.threshold(frameDelta, 10, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations = 2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) < 500: # Sensitivity
                continue

            motion_detected = True
            # Contour box around movement
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)

        return frame, motion_detected

    def update(self): # Live box around detected movement
        if self.cap is None or not self.cap.isOpened():
            return
        
        ret, frame = self.cap.read()
        if ret:
             if self.is_monitoring:                
                frame, motionDetected = self.motionDetection(frame)
                # Draw alert box around feed frame
                if motionDetected:
                    h, w = frame.shape[:2]
                    cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 10) # Perimeter box

                    cv2.putText(frame, "MOTION!", (w//2 - 50, 50), # Alert notification
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # -> Tkinter
        cv2_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2_im)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(frame.shape[1], frame.shape[0]))
        self.video_label.configure(image=ctk_img)
        self.video_label.image = ctk_img

        self.window.after(self.fps_delay, self.update)

    def onClosing(self): # Ensuring a clean close
        self.is_monitoring = False
        if self.cap.isOpened():
            self.cap.release()
        self.window.quit() # Stop main loop
        self.window.destroy()

# Entry
if __name__ == "__main__":
    root = ctk.CTk()
    accessCode = simpledialog.askstring("AUTHENTICATE", "Please Enter Access Code: ", show = '*', parent=root) # Prompting user for program passcode

    if accessCode == CORRECT_CODE:
        try:   
            app = MotionMonitoring(root)
            app.update() # Start loop
            root.mainloop()
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
    else:
        if accessCode is not None:
            messagebox.showerror("Error", "Wrong Code")
        root.destroy()
        sys.exit()