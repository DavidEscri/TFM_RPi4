from setuptools import setup, find_packages

setup(
    name='tfm_muaii_rpi4',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'setuptools~=69.0.3',
        'osmnx~=1.8.1',
        'geopy~=2.4.1',
        'python-dotenv~=1.0.0',
        'opencv-python~=4.7.0.72',
        'yolov5~=7.0.13',
        'PyYAML~=6.0.1',
        'torch~=2.1.2',
        'smbus2~=0.4.3',
    ],
    url='https://github.com/DavidEscri/TFM_RPi4',
    license='',
    author='Jose David Escribano Orts',
    author_email='davidescribano99@gmail.com',
    description='Paquete para distribuir el funcionamiento principal de la aplicación ejecutada en el RPi4'
)