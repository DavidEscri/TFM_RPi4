script_activate="/home/pi/tfm_env/bin/activate"

function ExitControl() {
      echo "Control de salida de la aplicación"
      case $S1 in
        1)
          echo "Reinicio del sistema"
          sleep 5
          # sudo reboot -r 'REINICIANDO EL SISTEMA'
        ;;
        2)
          echo "Apagado del sistema"
          # sudo shutdown 'APAGANDO EL SISTEMA'
        ;;
        *)
          echo "Reinicio del sistema (salida por defecto)"
          sleep 5
          # sudo shutdown -r 'REINICIANDO EL SISTEMA'
        ;;
      esac
      }

echo "INICIANDO SISTEMA"
echo "Activando entorno virtual python -> "  $script_activate
source $script_activate
$(python3.9 TFMApp.py)
output=$?
echo "SALIDA SISTEMA -> " $output
ExitControl $output