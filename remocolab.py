import apt, apt.debfile
import pathlib, stat, shutil, urllib.request, subprocess, getpass, time
import secrets, json, re
import IPython.utils.io

def _installPkg(cache, name):
  pkg = cache[name]
  if pkg.is_installed:
    print(f"{name} is already installed")
  else:
    print(f"Install {name}")
    pkg.mark_install()

def _installPkgs(cache, *args):
  for i in args:
    _installPkg(cache, i)

def _download(url, path):
  with urllib.request.urlopen(url) as response:
    with open(path, 'wb') as outfile:
      shutil.copyfileobj(response, outfile)

def _check_gpu_available():
  r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], stdout = subprocess.PIPE, universal_newlines = True)
  if r.returncode != 0:
    print("This is not a runtime with GPU")
  elif r.stdout == "Tesla K80\n":
    print("Warning! GPU of your assigned virtual machine is Tesla K80.")
    print("You might get better GPU by reseting the runtime.")
  else:
    return True

  return IPython.utils.io.ask_yes_no("Do you want to continue? [y/n]")

def _setupSSHDImpl(ngrok_token, ngrok_region):
  #apt-get update
  #apt-get upgrade
  cache = apt.Cache()
  cache.update()
  cache.open(None)
  cache.upgrade()
  cache.commit()

  subprocess.run(["unminimize"], input = "y\n", check = True, universal_newlines = True)

  _installPkg(cache, "openssh-server")
  cache.commit()

  #Reset host keys
  for i in pathlib.Path("/etc/ssh").glob("ssh_host_*_key"):
    i.unlink()
  subprocess.run(
                  ["ssh-keygen", "-A"],
                  check = True)

  #Prevent ssh session disconnection.
  with open("/etc/ssh/sshd_config", "a") as f:
    f.write("\n\nClientAliveInterval 120\n")

  print("ECDSA key fingerprint of host:")
  ret = subprocess.run(
                ["ssh-keygen", "-lvf", "/etc/ssh/ssh_host_ecdsa_key.pub"],
                stdout = subprocess.PIPE,
                check = True,
                universal_newlines = True)
  print(ret.stdout)

  _download("https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip", "ngrok.zip")
  shutil.unpack_archive("ngrok.zip")
  pathlib.Path("ngrok").chmod(stat.S_IXUSR)

  root_password = secrets.token_urlsafe()
  user_password = secrets.token_urlsafe()
  user_name = "colab"
  print("✂️"*24)
  print(f"root password: {root_password}")
  print(f"{user_name} password: {user_password}")
  print("✂️"*24)
  subprocess.run(["useradd", "-s", "/bin/bash", "-m", user_name])
  subprocess.run(["chpasswd"], input = f"root:{root_password}", universal_newlines = True)
  subprocess.run(["chpasswd"], input = f"{user_name}:{user_password}", universal_newlines = True)
  subprocess.run(["service", "ssh", "restart"])

  if not pathlib.Path('/root/.ngrok2/ngrok.yml').exists():
    subprocess.run(["./ngrok", "authtoken", ngrok_token])

  subprocess.Popen(["./ngrok", "tcp", "-region", ngrok_region, "22"])
  time.sleep(2)

  with urllib.request.urlopen("http://localhost:4040/api/tunnels") as response:
    url = json.load(response)['tunnels'][0]['public_url']
    m = re.match("tcp://(.+):(\d+)", url)

  hostname = m.group(1)
  port = m.group(2)

  ssh_common_options =  "-o UserKnownHostsFile=/dev/null -o VisualHostKey=yes"
  print("---")
  print("Command to connect to the ssh server:")
  print("✂️"*24)
  print(f"ssh {ssh_common_options} -p {port} {user_name}@{hostname}")
  print("✂️"*24)
  print("---")
  print("If you use VNC:")
  print("✂️"*24)
  print(f"ssh {ssh_common_options} -L 5901:localhost:5901 -p {port} {user_name}@{hostname}")
  print("✂️"*24)

def setupSSHD(ngrok_region = None, check_gpu_available = False):
  if check_gpu_available and not _check_gpu_available():
    return False

  print("---")
  print("Copy&paste your tunnel authtoken from https://dashboard.ngrok.com/auth")
  print("(You need to sign up for ngrok and login,)")
  #Set your ngrok Authtoken.
  ngrok_token = getpass.getpass()

  if not ngrok_region:
    print("Select your ngrok region:")
    print("us - United States (Ohio)")
    print("eu - Europe (Frankfurt)")
    print("ap - Asia/Pacific (Singapore)")
    print("au - Australia (Sydney)")
    print("sa - South America (Sao Paulo)")
    print("jp - Japan (Tokyo)")
    print("in - India (Mumbai)")
    ngrok_region = region = input()

  _setupSSHDImpl(ngrok_token, ngrok_region)
  return True

def _setupVNC():
  libjpeg_ver = "2.0.3"
  virtualGL_ver = "2.6.2"
  turboVNC_ver = "2.2.3"

  libjpeg_url = "https://svwh.dl.sourceforge.net/project/libjpeg-turbo/{0}/libjpeg-turbo-official_{0}_amd64.deb".format(libjpeg_ver)
  virtualGL_url = "https://svwh.dl.sourceforge.net/project/virtualgl/{0}/virtualgl_{0}_amd64.deb".format(virtualGL_ver)
  turboVNC_url = "https://svwh.dl.sourceforge.net/project/turbovnc/{0}/turbovnc_{0}_amd64.deb".format(turboVNC_ver)

  _download(libjpeg_url, "libjpeg-turbo.deb")
  _download(virtualGL_url, "virtualgl.deb")
  _download(turboVNC_url, "turbovnc.deb")
  cache = apt.Cache()
  apt.debfile.DebPackage("libjpeg-turbo.deb", cache).install()
  apt.debfile.DebPackage("virtualgl.deb", cache).install()
  apt.debfile.DebPackage("turbovnc.deb", cache).install()

  _installPkgs(cache, "xfce4", "xfce4-terminal")
  cache.commit()

  vnc_sec_conf_p = pathlib.Path("/etc/turbovncserver-security.conf")
  vnc_sec_conf_p.write_text("""\
no-remote-connections
no-httpd
no-x11-tcp-connections
""")

  # Install TESLA DRIVER FOR LINUX X64 ver418.67.
  # Kernel module in this driver is already loaded and cannot be neither removed nor updated.
  # (nvidia, nvidia_uvm, nvidia_drm. See dmesg)
  # Existing nvidia driver for Xorg is newer than these kernel module and cannot be used with Xorg.
  # So overwrite them with the nvidia driver that is same version to loaded kernel module.
  _download("http://us.download.nvidia.com/tesla/418.67/NVIDIA-Linux-x86_64-418.67.run", "nvidia.run")
  pathlib.Path("nvidia.run").chmod(stat.S_IXUSR)
  subprocess.run(["./nvidia.run", "--no-kernel-module", "--ui=none"], input = "1\n", check = True, universal_newlines = True)

  #https://virtualgl.org/Documentation/HeadlessNV
  subprocess.run(["nvidia-xconfig",
                  "-a",
                  "--allow-empty-initial-configuration",
                  "--virtual=1920x1200",
                  "--busid", "PCI:0:4:0"],
                 check = True
                )

  with open("/etc/X11/xorg.conf", "r") as f:
    conf = f.read()
    conf = re.sub('(Section "Device".*?)(EndSection)',
                  '\\1    MatchSeat      "seat-1"\n\\2',
                  conf,
                  1,
                  re.DOTALL)
  #  conf = conf + """
  #Section "Files"
  #    ModulePath "/usr/lib/xorg/modules"
  #    ModulePath "/usr/lib/x86_64-linux-gnu/nvidia-418/xorg/"
  #EndSection
  #"""

  with open("/etc/X11/xorg.conf", "w") as f:
    f.write(conf)

  #!service lightdm stop
  subprocess.run(["/opt/VirtualGL/bin/vglserver_config", "-config", "+s", "+f"], check = True)
  #user_name = "colab"
  #!usermod -a -G vglusers $user_name
  #!service lightdm start

  # Run Xorg server
  # VirtualGL and OpenGL application require Xorg running with nvidia driver to get Hardware 3D Acceleration.
  #
  # Without "-seat seat-1" option, Xorg try to open /dev/tty0 but it doesn't exists.
  # You can create /dev/tty0 with "mknod /dev/tty0 c 4 0" but you will get permision denied error.
  subprocess.Popen(["Xorg", "-seat", "seat-1", "-allowMouseOpenFail", "-novtswitch", "-nolisten", "tcp"])

  vncrun_py = pathlib.Path("vncrun.py")
  vncrun_py.write_text("""\
import subprocess, secrets, pathlib

vnc_passwd = secrets.token_urlsafe()[:8]
vnc_viewonly_passwd = secrets.token_urlsafe()[:8]
print("✂️"*24)
print("VNC password: {}".format(vnc_passwd))
print("VNC view only password: {}".format(vnc_viewonly_passwd))
print("✂️"*24)
vncpasswd_input = "{0}\\n{1}".format(vnc_passwd, vnc_viewonly_passwd)
vnc_user_dir = pathlib.Path.home().joinpath(".vnc")
vnc_user_dir.mkdir(exist_ok=True)
vnc_user_passwd = vnc_user_dir.joinpath("passwd")
with vnc_user_passwd.open('wb') as f:
  subprocess.run(
    ["/opt/TurboVNC/bin/vncpasswd", "-f"],
    stdout=f,
    input=vncpasswd_input,
    universal_newlines=True)
vnc_user_passwd.chmod(0o600)
subprocess.run(
  ["/opt/TurboVNC/bin/vncserver"]
)

#Disable screensaver because no one would want it.
(pathlib.Path.home() / ".xscreensaver").write_text("mode: off\\n")
""")
  r = subprocess.run(
                    ["su", "-c", "python3 vncrun.py", "colab"],
                    check = True,
                    stdout = subprocess.PIPE,
                    universal_newlines = True)
  print(r.stdout)

def setupVNC(ngrok_region = None):
  if setupSSHD(ngrok_region, True):
    _setupVNC()
