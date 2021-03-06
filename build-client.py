import os
import shutil
import glob
import zipfile

MCP_ZIP = 'http://bitbucket.org/Brunner/mcp/get/default.zip'
FERNFLOWER = 'https://github.com/Zidonuke/Bukkit-MinecraftServer/blob/master/tools/fernflower.jar?raw=true'

LWJGL_VERSION = '2.8.5'
lwjgl_jars = set(['jar/lwjgl.jar', 'jar/lwjgl_util.jar', 'jar/jinput.jar'])

def get_mcp(mcpzip=MCP_ZIP):
	import zipfile
	import urllib

	print('+ Deleting mcp directory')
	shutil.rmtree('mcp', True)

	print('+ Downloading newest mcp build')
	urllib.urlretrieve(mcpzip, 'mcp.zip')

	print('+ Extracting mcp')
	os.makedirs('mcp')
	with zipfile.ZipFile('mcp.zip', 'r') as z:
		z.extractall('mcp')
	
	os.unlink('mcp.zip')

def get_client_version():
	import re
	import urllib
	import ConfigParser

	with open('net/minecraft/client/Minecraft.java', 'r') as mcf:
		find = re.search('Minecraft (\d+(\.\d+)*)', mcf.read())
		if find is not None: v = find.group(1)
	
	mcv = urllib.urlopen('https://raw.github.com/MinecraftForge/FML/master/mc_versions.cfg')
	config = ConfigParser.SafeConfigParser()
	config.readfp(mcv)
	
	return v, config.get(v, 'client_url'), config.get(v, 'mcp_url')

def get_minecraft_jar(version=None, jarpath=None):
	import urllib

	print('+ Getting minecraft.jar for ' + version)

	jardir = os.path.join('jars', 'bin')
	try: os.makedirs(jardir)
	except OSError: pass

	urllib.urlretrieve(jarpath, 'jars/bin/minecraft.jar')

	print('+ Downloading fernflower.jar')
	urllib.urlretrieve(FERNFLOWER, 'runtime/bin/fernflower.jar')

	LWJGL = ('http://downloads.sourceforge.net/project/java-game-lib/Official Releases' +
		'/LWJGL ' + LWJGL_VERSION + '/lwjgl-' + LWJGL_VERSION + '.zip')
	
	print('+ Getting LWJGL ' + LWJGL_VERSION)
	urllib.urlretrieve(LWJGL, 'lwjgl.zip')

	print('+ Unzipping required LWJGL files')
	with open('lwjgl.zip', 'rb') as lwjgl_zip:
		z = zipfile.ZipFile(lwjgl_zip)
		for item in z.namelist():
			if any([item.endswith(k) for k in lwjgl_jars]):
				source = z.open(item)
				target = file(os.path.join(jardir, os.path.basename(item)), 'wb')
				with source, target: shutil.copyfileobj(source, target)
	
	try: os.makedirs(os.path.join(jardir, 'natives'))
	except OSError: pass

def decompile():
	print('+ Decompiling')
	import mcp.runtime.decompile
	mcp.runtime.decompile.main()

def recompile():
	import mcp.runtime.mcp as mcplib
	import mcp.runtime.commands as commands
	cmd = commands.Commands(None, verify=True)

	print('+ Recompiling')
	mcplib.recompile_side(cmd, commands.CLIENT)
	
	print('+ Reobfuscating')
	cmd.creatergcfg(reobf=True, keep_lvt=True, keep_generics=False, srg_names=False)
	mcplib.reobfuscate_side(cmd, commands.CLIENT, reobf_all=False, srg_names=False)

def package(root, zfile):
	print('+ Packaging client mod')
	resroot = os.path.join('..', 'resources')
	for src_path, dirs, files in os.walk(resroot):
		dst_path = src_path.replace(resroot, root)
		for file_ in files:
			src = os.path.join(src_path, file_)
			dst = os.path.join(dst_path, file_)
			
			try: os.makedirs(os.path.dirname(dst))
			except OSError: pass

			shutil.copy(src, dst)

	shutil.make_archive(zfile, 'zip', root)

src_dirs = set(['argo', 'net', 'org'])
def add_changes(src, dst):
	import codecs

	for src_dir, dirs, files in os.walk(src):
		dst_dir = src_dir.replace(src, dst)
		if not os.path.exists(dst_dir):
			os.mkdir(dst_dir)
		for file_ in files:
			src_file = os.path.join(src_dir, file_)
			dst_file = os.path.join(dst_dir, file_)
			print('# Copying: ' + src_file)
			if os.path.exists(dst_file):
				os.remove(dst_file)
			shutil.copy(src_file, dst_dir)

if __name__ == '__main__':
	os.chdir(os.path.dirname(os.path.realpath(__file__)))
	VERSION, CLIENT_JAR, MCP_ZIP = get_client_version()

	get_mcp(mcpzip=MCP_ZIP)
	os.chdir('mcp')
	
	# create a dummy init to treat mcp as a python module
	with open('__init__.py', 'w') as f: pass
	
	get_minecraft_jar(version=VERSION, jarpath=CLIENT_JAR)
	decompile()

	for d in src_dirs:
		target = os.path.join('src', 'minecraft', d)
		add_changes(src=os.path.join('..', d), dst=target)
	
	recompile()
	package(os.path.join('reobf', 'minecraft'), 
		os.path.join('..', 'AutoReferee-client-' + VERSION))
