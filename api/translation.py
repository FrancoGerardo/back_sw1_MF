from googletrans import Translator, LANGUAGES
# 1. No necesitamos importar asyncio

def translate_text(text, target_language, source_language=None):
    """
    Traduce un texto usando la librería googletrans (versión síncrona).
    """
    # Validar que el idioma de destino sea válido
    if target_language not in LANGUAGES:
        return {'error': f"El idioma de destino '{target_language}' no es válido."}

    # --- INICIO DE LA CORRECCIÓN ---
    # La librería es síncrona. Eliminamos async/await.
    try:
        translator = Translator()
        
        # Simplemente llamamos a la función, sin 'await'
        if source_language and source_language in LANGUAGES:
            translation = translator.translate(text, dest=target_language, src=source_language)
        else:
            translation = translator.translate(text, dest=target_language)

        return {
            'translated_text': translation.text,
            'detected_source_language': translation.src
        }
    # --- FIN DE LA CORRECCIÓN ---
    except Exception as e:
        # El error que viste (can't be used in 'await' expression)
        # se estaba generando aquí.
        return {'error': f"Ocurrió un error during la traducción: {str(e)}"}