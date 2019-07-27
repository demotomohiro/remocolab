# remocolab
remocolab is a Python module to allow remote access to [Google Colaboratory](https://colab.research.google.com/) using SSH or [TurboVNC](https://www.turbovnc.org/).
It also install [VirtualGL](https://www.virtualgl.org/) so that you can run OpenGL programs on a Google Colaboratory machine and see the screen on VNC client.
It secures TurboVNC connection using SSH port forwarding.

## Requirements
- You can use [Google Colaboratory](https://colab.research.google.com/)
  - That means you need Google acount and a browser that is supported by Google Colaboratory.
- [ngrok](https://ngrok.com/) Tunnel Authtoken
  - You need to sign up for ngrok to get it
- SSH client
- (Optional) TurboVNC Viewer if you use it.

## How to use
1. Create a new notebook on Google Colaboratory
2. Add a code cell and copy & paste one of following codes to the cell

- SSH only:
```python3
!pip install git+https://github.com/demotomohiro/remocolab.git
import remocolab
remocolab.setupSSHD()
```

- SSH and TurboVNC:
```python3
!pip install git+https://github.com/demotomohiro/remocolab.git
import remocolab
remocolab.setupVNC()
```

3. (Optional) If you want to run OpenGL applications or any programs that use GPU,
Click "Runtime" -> "Change runtime type" in top menu and change Hardware accelerator to GPU. 
4. Run that cell
5. Then the message that ask you to copy & paste tunnel authtoken of ngrok will appear.
Login to ngrok, click Auth on left side menu, click Copy, return to Google Colaboratory, paste it to the text box under the message and push enter key.
6. Select your ngrok region. Select the one closest to your location. For example, if you were in Japan, type jp and push enter key.
7. remocolab setup ngrok and SSH server. Please wait for it done (about 2 minutes)
8. Then, root and colab user password and ssh command to connect the server will appear.
9. Copy & paste the ssh command to your terminal and login to the server using displayed colab user password.

