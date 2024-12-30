from setuptools import setup, find_packages

setup(
    name='tfm_muaii_rpi4',
    version='0.8.7',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'setuptools~=65.5.1',
        'build~=1.2.1',
        'geopy~=2.4.1',
        'python-dotenv~=1.0.0',
        'opencv-python~=4.7.0.72',
        'PyYAML~=6.0.1',
        'numpy==1.26.4',
        'ultralytics==8.3.53',
        'torchvision~=0.16.2',
        'torch~=2.1.2',
        'smbus2~=0.4.3',
        'Pillow~=10.1.0',
        'luma.oled~=3.13.0',
        'Rtree~=1.2.0',
        'typing-extensions~=4.12.2',
        'picamera2~=0.3.12',
        'folium==0.19.2'
    ],
    url='https://github.com/DavidEscri/TFM_RPi4',
    license='',
    author='Jose David Escribano Orts',
    author_email='davidescribano99@gmail.com',
    description='Paquete para distribuir el funcionamiento principal de la aplicación ejecutada en el RPi4'
)