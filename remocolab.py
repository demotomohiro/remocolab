import apt, apt.debfile
import pathlib, stat, shutil, urllib.request, subprocess, getpass, time, tempfile
import secrets, json, re
import IPython.utils.io
import ipywidgets
import pyngrok.ngrok, pyngrok.conf

# https://salsa.debian.org/apt-team/python-apt
# https://apt-team.pages.debian.net/python-apt/library/index.html
class _NoteProgress(apt.progress.base.InstallProgress, apt.progress.base.AcquireProgress, apt.progress.base.OpProgress):
  def __init__(self):
    apt.progress.base.InstallProgress.__init__(self)
    self._label = ipywidgets.Label()
    display(self._label)
    self._float_progress = ipywidgets.FloatProgress(min = 0.0, max = 1.0, layout = {'border':'1px solid #118800'})
    display(self._float_progress)

  def close(self):
    self._float_progress.close()
    self._label.close()

  def fetch(self, item):
    self._label.value = "fetch: " + item.shortdesc

  def pulse(self, owner):
    self._float_progress.value = self.current_items / self.total_items
    return True

  def status_change(self, pkg, percent, status):
    self._label.value = "%s: %s" % (pkg, status)
    self._float_progress.value = percent / 100.0

  def update(self, percent=None):
    self._float_progress.value = self.percent / 100.0
    self._label.value = self.op + ": " + self.subop

  def done(self, item=None):
    pass

class _MyApt:
  def __init__(self):
    self._progress = _NoteProgress()
    self._cache = apt.Cache(self._progress)

  def close(self):
    self._cache.close()
    self._cache = None
    self._progress.close()
    self._progress = None

  def update_upgrade(self):
    self._cache.update()
    self._cache.open(None)
    self._cache.upgrade()

  def commit(self):
    self._cache.commit(self._progress, self._progress)
    self._cache.clear()

  def installPkg(self, *args):
    for name in args:
      pkg = self._cache[name]
      if pkg.is_installed:
        print(f"{name} is already installed")
      else:
        print(f"Install {name}")
        pkg.mark_install()

  def installDebPackage(self, name):
    apt.debfile.DebPackage(name, self._cache).install()

  def deleteInstalledPkg(self, *args):
    for pkg in self._cache:
      if pkg.is_installed:
        for name in args:
          if pkg.name.startswith(name):
            #print(f"Delete {pkg.name}")
            pkg.mark_delete()

def _download(url, path):
  try:
    with urllib.request.urlopen(url) as response:
      with open(path, 'wb') as outfile:
        shutil.copyfileobj(response, outfile)
  except:
    print("Failed to download ", url)
    raise

def _get_gpu_name():
  r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], stdout = subprocess.PIPE, universal_newlines = True)
  if r.returncode != 0:
    return None
  return r.stdout.strip()

def _check_gpu_available():
  gpu_name = _get_gpu_name()
  if gpu_name == None:
    print("This is not a runtime with GPU")
  elif gpu_name == "Tesla K80":
    print("Warning! GPU of your assigned virtual machine is Tesla K80.")
    print("You might get better GPU by reseting the runtime.")
  else:
    return True

  return IPython.utils.io.ask_yes_no("Do you want to continue? [y/n]")

def _set_public_key(user, public_key):
  if public_key != None:
    home_dir = pathlib.Path("/root" if user == "root" else "/home/" + user)
    ssh_dir = home_dir / ".ssh"
    ssh_dir.mkdir(mode = 0o700, exist_ok=True)
    auth_keys_file = ssh_dir / "authorized_keys"
    auth_keys_file.write_text(public_key)
    auth_keys_file.chmod(0o600)
    if user != "root":
      shutil.chown(ssh_dir, user)
      shutil.chown(auth_keys_file, user)

def _setupSSHDImpl(public_key, tunnel, ngrok_token, ngrok_region, mount_gdrive_to, mount_gdrive_from, is_VNC):
  #apt-get update
  #apt-get upgrade
  my_apt = _MyApt()
  #Following packages are useless because nvidia kernel modules are already loaded and I cannot remove or update it.
  #Uninstall them because upgrading them take long time.
  my_apt.deleteInstalledPkg("nvidia-dkms", "nvidia-kernel-common", "nvidia-kernel-source")
  my_apt.commit()
  my_apt.update_upgrade()
  my_apt.commit()

  subprocess.run(["unminimize"], input = "y\n", check = True, universal_newlines = True)

  my_apt.installPkg("openssh-server")
  if mount_gdrive_to:
    my_apt.installPkg("bindfs")

  my_apt.commit()
  my_apt.close()

  #Reset host keys
  for i in pathlib.Path("/etc/ssh").glob("ssh_host_*_key"):
    i.unlink()
  subprocess.run(
                  ["ssh-keygen", "-A"],
                  check = True)

  #Prevent ssh session disconnection.
  with open("/etc/ssh/sshd_config", "a") as f:
    f.write("\n\n# Options added by remocolab\n")
    f.write("ClientAliveInterval 120\n")
    if public_key != None:
      f.write("PasswordAuthentication no\n")

  msg = ""
  msg += "ED25519 key fingerprint of host:\n"
  ret = subprocess.run(
                ["ssh-keygen", "-lvf", "/etc/ssh/ssh_host_ed25519_key.pub"],
                stdout = subprocess.PIPE,
                check = True,
                universal_newlines = True)
  msg += ret.stdout + "\n"

  root_password = secrets.token_urlsafe()
  user_password = secrets.token_urlsafe()
  user_name = "colab"
  msg += "✂️"*24 + "\n"
  msg += f"root password: {root_password}\n"
  msg += f"{user_name} password: {user_password}\n"
  msg += "✂️"*24 + "\n"
  subprocess.run(["useradd", "-s", "/bin/bash", "-m", user_name])
  subprocess.run(["adduser", user_name, "sudo"], check = True)
  subprocess.run(["chpasswd"], input = f"root:{root_password}", universal_newlines = True)
  subprocess.run(["chpasswd"], input = f"{user_name}:{user_password}", universal_newlines = True)
  subprocess.run(["service", "ssh", "restart"])
  _set_public_key(user_name, public_key)

  if mount_gdrive_to:
    user_gdrive_dir = pathlib.Path("/home") / user_name / mount_gdrive_to
    pathlib.Path(user_gdrive_dir).mkdir(parents = True)
    gdrive_root = pathlib.Path("/content/drive")
    target_gdrive_dir = (gdrive_root / mount_gdrive_from) if mount_gdrive_from else gdrive_root
    subprocess.run(["bindfs", "-u", user_name, "-g", user_name, target_gdrive_dir, user_gdrive_dir], check = True)

  ssh_common_options =  "-o UserKnownHostsFile=/dev/null -o VisualHostKey=yes"

  if tunnel == "ngrok":
    pyngrok_config = pyngrok.conf.PyngrokConfig(auth_token = ngrok_token, region = ngrok_region)
    ssh_tunnel = pyngrok.ngrok.connect(addr = 22, proto = "tcp", pyngrok_config = pyngrok_config)
    m = re.match("tcp://(.+):(\d+)", ssh_tunnel.public_url)
    hostname = m.group(1)
    port = m.group(2)
    ssh_common_options += f" -p {port}"
  elif tunnel == "argotunnel":
    _download("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", "cloudflared")
    #shutil.unpack_archive("cloudflared.tgz")
    pathlib.Path("cloudflared").chmod(stat.S_IXUSR)
    cfd_proc = subprocess.Popen(
        ["./cloudflared", "tunnel", "--url", "ssh://localhost:22", "--logfile", "cloudflared.log", "--metrics", "localhost:49589"],
        stdout = subprocess.PIPE,
        universal_newlines = True
        )
    time.sleep(4)
    # Checking if child process has terminated is meaningless because recent version of cloudflared creates new a process and quit soon.
    # if cfd_proc.poll() != None:
    #   raise RuntimeError("Failed to run cloudflared. Return code:" + str(cfd_proc.returncode) + "\nSee clouldflared.log for more info.")
    hostname = None
    # Sometimes it takes long time to display user host name in cloudflared metrices.
    for i in range(20):
      with urllib.request.urlopen("http://127.0.0.1:49589/metrics") as response:
        text = str(response.read())
        sub = "\\ncloudflared_tunnel_user_hostnames_counts{userHostname=\"https://"
        begin = text.find(sub)
        if begin == -1:
          time.sleep(10)
          #print("Retry reading cloudflared user hostname")
          continue
        end = text.index("\"", begin + len(sub))
        hostname = text[begin + len(sub) : end]
        break
    if hostname == None:
      raise RuntimeError("Failed to get user hostname from cloudflared")
    ssh_common_options += " -oProxyCommand=\"cloudflared access ssh --hostname %h\""

  msg += "---\n"
  if is_VNC:
    msg += "Execute following command on your local machine and login before running TurboVNC viewer:\n"
    msg += "✂️"*24 + "\n"
    msg += f"ssh {ssh_common_options} -L 5901:localhost:5901 {user_name}@{hostname}\n"
  else:
    msg += "Command to connect to the ssh server:\n"
    msg += "✂️"*24 + "\n"
    msg += f"ssh {ssh_common_options} {user_name}@{hostname}\n"
    msg += "✂️"*24 + "\n"
  return msg

def _setupSSHDMain(public_key, tunnel, ngrok_region, check_gpu_available, mount_gdrive_to, mount_gdrive_from, is_VNC):
  if check_gpu_available and not _check_gpu_available():
    return (False, "")

  print("---")
  if tunnel == None:
    print("As ngrok doesn't work on colab for long time, default tunnel method has been changed to Argo tunnel.")
    print("Please read this for more details:")
    print("https://github.com/demotomohiro/remocolab/blob/master/README.md")
    tunnel = "argotunnel"

  avail_tunnels = {"ngrok", "argotunnel"}
  if tunnel not in avail_tunnels:
    raise RuntimeError("tunnel argument must be one of " + str(avail_tunnels))

  if mount_gdrive_to:
    if not pathlib.Path('/content/drive').exists():
      print("Please click the folder icon on left side of Google Colab and Mount Drive.")
      return (False, "")

    if mount_gdrive_from:
      try:
        gdrive_root = pathlib.Path("/content/drive").joinpath(mount_gdrive_from).resolve(strict = True)
        gdrive_root_parts = gdrive_root.parts
        if len(gdrive_root_parts) < 2 or gdrive_root_parts[1] != "content":
          raise FileNotFoundError
      except FileNotFoundError:
        print("Please specifiy the existing directory path in your Google drive like 'mount_gdrive_from = \"My Drive/somedir\"'")
        return (False, "")

  ngrok_token = None

  if tunnel == "ngrok":
    print("It seems Google is blocking ngrok.")
    print("If you got error 'kex_exchange_identification: Connection closed by remote host' when you login to ssh, you need to use Argo Tunnel instead of ngrok.")
    print("Please read this for more details:")
    print("https://github.com/demotomohiro/remocolab/blob/master/README.md")
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

  return (True, _setupSSHDImpl(public_key, tunnel, ngrok_token, ngrok_region, mount_gdrive_to, mount_gdrive_from, is_VNC))

def setupSSHD(ngrok_region = None, check_gpu_available = False, tunnel = None, mount_gdrive_to = None, mount_gdrive_from = None, public_key = None):
  s, msg = _setupSSHDMain(public_key, tunnel, ngrok_region, check_gpu_available, mount_gdrive_to, mount_gdrive_from, False)
  print(msg)

def _setup_nvidia_gl():
  # Install TESLA DRIVER FOR LINUX X64.
  # Kernel module in this driver is already loaded and cannot be neither removed nor updated.
  # (nvidia, nvidia_uvm, nvidia_drm. See dmesg)
  # Version number of nvidia driver for Xorg must match version number of these kernel module.
  # But existing nvidia driver for Xorg might not match.
  # So overwrite them with the nvidia driver that is same version to loaded kernel module.
  ret = subprocess.run(
                  ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                  stdout = subprocess.PIPE,
                  check = True,
                  universal_newlines = True)
  nvidia_version = ret.stdout.strip()
  nvidia_url = "https://us.download.nvidia.com/tesla/{0}/NVIDIA-Linux-x86_64-{0}.run".format(nvidia_version)
  _download(nvidia_url, "nvidia.run")
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

def _setupVNC():
  libjpeg_ver = "2.0.5"
  virtualGL_ver = "2.6.4"
  turboVNC_ver = "2.2.5"

  libjpeg_url = "https://github.com/demotomohiro/turbovnc/releases/download/2.2.5/libjpeg-turbo-official_{0}_amd64.deb".format(libjpeg_ver)
  virtualGL_url = "https://github.com/demotomohiro/turbovnc/releases/download/2.2.5/virtualgl_{0}_amd64.deb".format(virtualGL_ver)
  turboVNC_url = "https://github.com/demotomohiro/turbovnc/releases/download/2.2.5/turbovnc_{0}_amd64.deb".format(turboVNC_ver)

  _download(libjpeg_url, "libjpeg-turbo.deb")
  _download(virtualGL_url, "virtualgl.deb")
  _download(turboVNC_url, "turbovnc.deb")
  my_apt = _MyApt()
  my_apt.installDebPackage("libjpeg-turbo.deb")
  my_apt.installDebPackage("virtualgl.deb")
  my_apt.installDebPackage("turbovnc.deb")

  my_apt.installPkg("xfce4", "xfce4-terminal")
  my_apt.commit()
  my_apt.close()

  vnc_sec_conf_p = pathlib.Path("/etc/turbovncserver-security.conf")
  vnc_sec_conf_p.write_text("""\
no-remote-connections
no-httpd
no-x11-tcp-connections
""")

  gpu_name = _get_gpu_name()
  if gpu_name != None:
    _setup_nvidia_gl()

  vncrun_py = tempfile.gettempdir() / pathlib.Path("vncrun.py")
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
  ["/opt/TurboVNC/bin/vncserver"],
  cwd = pathlib.Path.home()
)

#Disable screensaver because no one would want it.
(pathlib.Path.home() / ".xscreensaver").write_text("mode: off\\n")
""")
  r = subprocess.run(
                    ["su", "-c", "python3 " + str(vncrun_py), "colab"],
                    check = True,
                    stdout = subprocess.PIPE,
                    universal_newlines = True)
  return r.stdout

def setupVNC(ngrok_region = None, check_gpu_available = True, tunnel = None, mount_gdrive_to = None, mount_gdrive_from = None, public_key = None):
  stat, msg = _setupSSHDMain(public_key, tunnel, ngrok_region, check_gpu_available, mount_gdrive_to, mount_gdrive_from, True)
  if stat:
    msg += _setupVNC()

  print(msg)
