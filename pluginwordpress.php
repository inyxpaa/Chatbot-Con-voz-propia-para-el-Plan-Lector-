<?php

if (!defined('ABSPATH')) {
    exit;
}

function mostrar_buscador_ia_widget() {

    $url = "https://buscador-ia.com/";

    $salida = '<div class="contenedor-buscador-ia" style="width: 100%; max-width: 1000px; margin: 0 auto; overflow: hidden;">';
    $salida .= '<iframe src="' . $url . '" 
                    width="100%" 
                    height="700px" 
                    style="border: 2px solid #007cba; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);" 
                    allowfullscreen 
                    title="Buscador IA">
                </iframe>';
    $salida .= '</div>';

    return $salida;
}

add_shortcode('buscador_ia', 'mostrar_buscador_ia_widget');
?>