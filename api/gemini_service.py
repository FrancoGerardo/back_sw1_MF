import google.generativeai as genai
import os
from django.conf import settings
from .models import Document, Folder, Tag, DocumentPermission
from django.contrib.auth.models import User
from .text_extractor import extract_text
from django.core.files.base import ContentFile
import json
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Configurar Gemini
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

class GeminiAssistant:
    def __init__(self, user):
        self.user = user
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def process_command(self, prompt):
        """
        Procesa el comando del usuario y ejecuta la acción correspondiente
        """
        # Obtener contexto de documentos y carpetas del usuario
        documents = Document.objects.filter(owner=self.user)
        folders = Folder.objects.filter(owner=self.user)
        
        context = self._build_context(documents, folders)
        
        # Crear el prompt completo para Gemini
        full_prompt = f"""
        Eres un asistente de gestión de documentos. Tienes acceso a los siguientes documentos y carpetas del usuario:
        
        {context}
        
        El usuario solicita: {prompt}
        
        Analiza la solicitud y responde SOLO con un JSON válido con esta estructura:
        {{
            "action": "tag_document|tag_all|create_mindmap|upload_document|summarize|translate|organize|share_permission|create_tag|rename_tag|delete_tag",
            "parameters": {{
                // parámetros específicos según la acción
            }},
            "message": "Mensaje descriptivo de lo que se hará"
        }}
        
Acciones disponibles:
        - tag_document: (params: document_id, tag_name) Etiquetar un documento específico
        - tag_all: Etiquetar todos los documentos
        - create_mindmap: Crear mapa conceptual de un documento
        - upload_document: Crear y subir un documento nuevo
        - summarize: (params: document_id, target_folder [opcional]) Resumir un documento. Si se especifica target_folder, guardar ahí; si no, usar la carpeta del documento original
        - translate: Traducir un documento
        - organize: Organizar documento en carpeta
        - share_permission: (params: [document_id o document_name], username, permission) Compartir documento con usuario
        - create_tag: Crear una nueva etiqueta sin asignarla a ningún documento
        - rename_tag: (params: old_tag_name, new_tag_name) Renombrar una etiqueta existente
        - delete_tag: (params: tag_name) Eliminar una etiqueta existente
        - delete_document: (params: document_id o document_name) Eliminar un documento específico
        - delete_all_documents: Eliminar todos los documentos del usuario
        - delete_all_tags: Eliminar todas las etiquetas del usuario
        """
        
        try:
            response = self.model.generate_content(full_prompt)
            
            raw_text = response.text
            
            json_start = raw_text.find('{')
            json_end = raw_text.rfind('}')
            
            if json_start == -1 or json_end == -1:
                raise ValueError("La respuesta de la IA no contenía un JSON válido.")

            json_string = raw_text[json_start:json_end+1]
            
            action_data = json.loads(json_string)
            
            result = self._execute_action(action_data)
            return result
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al procesar el comando: {str(e)}'
            }
    
    def _build_context(self, documents, folders):
        """Construye el contexto de documentos, carpetas y etiquetas"""
        context = "DOCUMENTOS:\n"
        for doc in documents:
            context += f"- ID: {doc.id}, Nombre: {doc.file.name}, Carpeta: {doc.folder.name if doc.folder else 'Raíz'}\n"
        
        context += "\nCARPETAS:\n"
        for folder in folders:
            context += f"- ID: {folder.id}, Nombre: {folder.name}\n"
        
        # --- INICIO DE LA MODIFICACIÓN ---
        context += "\nETIQUETAS EXISTENTES:\n"
        tags = Tag.objects.filter(owner=self.user)
        for tag in tags:
            context += f"- Nombre: {tag.name}\n"
        # --- FIN DE LA MODIFICACIÓN ---

        return context
    
    def _execute_action(self, action_data):
        """Ejecuta la acción determinada por Gemini"""
        action = action_data.get('action')
        params = action_data.get('parameters', {})

        if action == 'create_mindmap':
            if self.user.profile.subscription_plan != 'premium':
                return {
                    'success': False, 
                    'message': '🔒 La función de Mapas Conceptuales es exclusiva para usuarios Premium. ¡Actualiza tu plan!'
                }
        
        try:
            if action == 'tag_document':
                return self._tag_document(params)
            elif action == 'tag_all':
                return self._tag_all_documents(params)
            elif action == 'create_mindmap':
                return self._create_mindmap(params)
            elif action == 'upload_document':
                return self._upload_document(params)
            elif action == 'summarize':
                return self._summarize_document(params)
            elif action == 'translate':
                return self._translate_document(params)
            elif action == 'organize':
                return self._organize_document(params)
            elif action == 'share_permission':
                return self._share_permission(params)
            elif action == 'create_tag':
                return self._create_tag(params)
            elif action == 'rename_tag':
                return self._rename_tag(params)
            elif action == 'delete_tag':
                return self._delete_tag(params)
            elif action == 'delete_document':
                return self._delete_document(params)
            elif action == 'delete_all_documents':
                return self._delete_all_documents(params)
            elif action == 'delete_all_tags':
                return self._delete_all_tags(params)
            else:
                return {'success': False, 'message': 'Acción no reconocida'}
        except Exception as e:
            return {'success': False, 'message': f'Error ejecutando acción: {str(e)}'}
            
    def _tag_document(self, params):
        """Etiqueta un documento específico"""
        doc_id = params.get('document_id')
        tag_name = params.get('tag_name')
        
        document = Document.objects.get(id=doc_id, owner=self.user)
        tag, created = Tag.objects.get_or_create(name=tag_name, owner=self.user)
        document.tags.add(tag)
        
        return {
            'success': True,
            'message': f'Etiqueta "{tag_name}" asignada al documento {document.file.name}'
        }

    def _tag_all_documents(self, params):
        """Etiqueta todos los documentos según su contenido"""
        documents = Document.objects.filter(owner=self.user)
        tagged_count = 0
        
        for doc in documents:
            if doc.extracted_content:
                # Usar Gemini para sugerir etiquetas
                prompt = f"Analiza este contenido y sugiere UNA etiqueta corta (máx 2 palabras):\n\n{doc.extracted_content[:500]}"
                response = self.model.generate_content(prompt)
                tag_name = response.text.strip().replace('"', '')
                
                tag, created = Tag.objects.get_or_create(name=tag_name, owner=self.user)
                doc.tags.add(tag)
                tagged_count += 1
        
        return {
            'success': True,
            'message': f'{tagged_count} documentos etiquetados automáticamente'
        }
    
    def _create_mindmap(self, params):
        """Crea un mapa conceptual de un documento en formato HTML interactivo"""
        doc_id = params.get('document_id')
        
        # Buscar el documento de forma más flexible
        try:
            document = Document.objects.get(id=doc_id, owner=self.user)
        except Document.DoesNotExist:
            return {
                'success': False,
                'message': f'No se encontró el documento con ID {doc_id} o no tienes permisos para acceder a él.'
            }
        except ValueError:
            return {
                'success': False,
                'message': f'El ID proporcionado "{doc_id}" no es válido. Debe ser un número.'
            }
        
        # Verificar que el documento tenga contenido extraído
        if not document.extracted_content or document.extracted_content.strip() == "":
            filename = os.path.basename(document.file.name)
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Mensaje específico según el tipo de archivo
            if file_ext in ['.docx', '.doc']:
                message = f'⚠️ El documento "{filename}" aún no ha sido procesado. Los archivos .docx pueden tardar unos segundos. Por favor, recarga la página e intenta nuevamente en 10 segundos.'
            elif file_ext == '.pdf':
                message = f'⚠️ El documento "{filename}" no tiene contenido extraído. Puede ser un PDF escaneado (imagen). Intenta con otro documento o espera a que se procese.'
            else:
                message = f'⚠️ El documento "{filename}" no tiene contenido de texto extraíble. Tipo de archivo: {file_ext}'
            
            return {
                'success': False,
                'message': message
            }
        
# Generar mapa conceptual con Gemini en formato estructurado
        prompt = f"""
        Crea un mapa conceptual VISUAL del siguiente contenido en HTML.
        
        ESTRUCTURA REQUERIDA:
        1. Título principal centrado en la parte superior
        2. Concepto central en el medio (en un recuadro grande)
        3. Ramas que salen del concepto central hacia los lados
        4. Cada rama tiene subconceptos conectados
        
        USA EXACTAMENTE ESTE TEMPLATE HTML:
        
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Mapa Conceptual</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 40px;
                    margin: 0;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                h1 {{
                    text-align: center;
                    color: #2c3e50;
                    margin-bottom: 50px;
                    font-size: 2.5em;
                }}
                .mindmap {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 40px;
                }}
                .central {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px 50px;
                    border-radius: 20px;
                    font-size: 1.8em;
                    font-weight: bold;
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
                    max-width: 400px;
                }}
                .branches {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 30px;
                    width: 100%;
                    margin-top: 30px;
                }}
                .branch {{
                    background: #f8f9fa;
                    padding: 25px;
                    border-radius: 15px;
                    border-left: 5px solid #667eea;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }}
                .branch-title {{
                    font-size: 1.3em;
                    font-weight: bold;
                    color: #667eea;
                    margin-bottom: 15px;
                }}
                .subconcept {{
                    background: white;
                    padding: 12px 18px;
                    margin: 10px 0;
                    border-radius: 10px;
                    border-left: 3px solid #764ba2;
                    font-size: 1em;
                    color: #2c3e50;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>[TÍTULO DEL DOCUMENTO]</h1>
                <div class="mindmap">
                    <div class="central">[CONCEPTO CENTRAL]</div>
                    <div class="branches">
                        <div class="branch">
                            <div class="branch-title">[RAMA 1]</div>
                            <div class="subconcept">[Subconcepto 1.1]</div>
                            <div class="subconcept">[Subconcepto 1.2]</div>
                        </div>
                        <!-- Repite para más ramas -->
                    </div>
                </div>
            </div>
        </body>
        </html>
        
        INSTRUCCIONES:
        - Reemplaza [TÍTULO DEL DOCUMENTO] con un título descriptivo
        - Reemplaza [CONCEPTO CENTRAL] con el tema principal
        - Crea 4-6 ramas principales [RAMA 1, RAMA 2, etc]
        - Cada rama debe tener 2-4 subconceptos
        - NO agregues texto explicativo, SOLO devuelve el HTML
        
        Contenido a analizar:
        {document.extracted_content[:3000]}
        """
        
        response = self.model.generate_content(prompt)
        mindmap_html = response.text
        
        # Limpiar el HTML si viene con markdown
        if '```html' in mindmap_html:
            mindmap_html = mindmap_html.split('```html')[1].split('```')[0].strip()
        elif '```' in mindmap_html:
            mindmap_html = mindmap_html.split('```')[1].split('```')[0].strip()
        
        # Crear el documento HTML
        filename = f"mapa_conceptual_{os.path.basename(document.file.name).split('.')[0]}.html"
        new_doc = Document.objects.create(
            owner=self.user,
            folder=document.folder,
            file=ContentFile(mindmap_html.encode('utf-8'), name=filename),
            extracted_content=mindmap_html  # Guardar el HTML también como contenido
        )
        
        return {
            'success': True,
            'message': f'✅ Mapa conceptual creado exitosamente',
            'document_id': new_doc.id,
            'document_name': filename,
            'download_url': new_doc.file.url,
            'show_download': True  # Flag para que el frontend muestre el botón de descarga
        }
    
    def _upload_document(self, params):
        """Crea y sube un documento nuevo"""
        folder_name = params.get('folder_name')
        topic = params.get('topic')
        doc_type = params.get('type', 'pdf')
        
        # Generar contenido con Gemini
        prompt = f"Escribe un documento completo sobre: {topic}. Debe ser informativo y bien estructurado."
        response = self.model.generate_content(prompt)
        content = response.text
        
        # Buscar o crear carpeta
        folder = None
        if folder_name:
            folder, created = Folder.objects.get_or_create(name=folder_name, owner=self.user)
        
        # Crear documento
        filename = f"{topic.replace(' ', '_')}.txt"
        new_doc = Document.objects.create(
            owner=self.user,
            folder=folder,
            file=ContentFile(content.encode('utf-8'), name=filename),
            extracted_content=content
        )
        
        return {
            'success': True,
            'message': f'Documento "{filename}" creado y subido a {folder_name or "Raíz"}',
            'document_id': new_doc.id
        }
    
    def _summarize_document(self, params):
        """Resume un documento"""
        doc_id = params.get('document_id')
        create_new = params.get('create_new', True)
        target_folder = params.get('target_folder')
        
        document = Document.objects.get(id=doc_id, owner=self.user)
        
        # Generar resumen
        prompt = f"Resume el siguiente texto de manera concisa:\n\n{document.extracted_content}"
        response = self.model.generate_content(prompt)
        summary = response.text
        
        if create_new:
            # Determinar carpeta destino
            folder = None
            if target_folder:
                # Si se especificó una carpeta, buscarla o crearla
                folder, created = Folder.objects.get_or_create(name=target_folder, owner=self.user)
            else:
                # Si no se especificó, usar la misma carpeta del documento original
                folder = document.folder
            
            filename = f"resumen_{document.file.name}"
            new_doc = Document.objects.create(
                owner=self.user,
                folder=folder,
                file=ContentFile(summary.encode('utf-8'), name=filename),
                extracted_content=summary
            )
            
            return {
                'success': True,
                'message': f'Resumen creado: {filename}',
                'document_id': new_doc.id
            }
        else:
            # Actualizar documento existente
            document.extracted_content = summary
            document.save()
            
            return {
                'success': True,
                'message': f'Documento actualizado con resumen'
            }
    
    def _translate_document(self, params):
        """Traduce un documento"""
        doc_id = params.get('document_id')
        target_lang = params.get('target_language', 'es')
        
        document = Document.objects.get(id=doc_id, owner=self.user)
        
        # Traducir con Gemini
        prompt = f"Traduce el siguiente texto a {target_lang}:\n\n{document.extracted_content}"
        response = self.model.generate_content(prompt)
        translated_text = response.text
        
        # Actualizar documento
        document.extracted_content = translated_text
        document.save()
        
        return {
            'success': True,
            'message': f'Documento traducido a {target_lang}'
        }
    
    def _organize_document(self, params):
        """Organiza un documento en una carpeta"""
        doc_id = params.get('document_id')
        document = Document.objects.get(id=doc_id, owner=self.user)
        
        # Analizar contenido para sugerir carpeta
        prompt = f"Basándote en este contenido, sugiere UN nombre de carpeta corto (máx 3 palabras) para organizarlo:\n\n{document.extracted_content[:500]}"
        response = self.model.generate_content(prompt)
        folder_name = response.text.strip().replace('"', '')
        
        # Crear o buscar carpeta
        folder, created = Folder.objects.get_or_create(name=folder_name, owner=self.user)
        document.folder = folder
        document.save()
        
        return {
            'success': True,
            'message': f'Documento movido a carpeta "{folder_name}"'
        }
    

    def _create_tag(self, params):
        """Crea una nueva etiqueta sin asignarla a un documento"""
        tag_name = params.get('tag_name')
        
        if not tag_name:
            return {'success': False, 'message': 'La IA no proporcionó un nombre para la etiqueta'}

        # Crear o buscar la etiqueta
        tag, created = Tag.objects.get_or_create(name=tag_name, owner=self.user)
        
        if created:
            message = f'Etiqueta "{tag_name}" creada exitosamente'
        else:
            message = f'La etiqueta "{tag_name}" ya existía'
            
        return {
            'success': True,
            'message': message,
            'tag_id': tag.id
        }

    def _share_permission(self, params):
        """Comparte un documento con un usuario"""
        doc_id = params.get('document_id')
        doc_name = params.get('document_name')
        username = params.get('username')
        permission = params.get('permission', 'view')
        
        # --- INICIO DE LA CORRECCIÓN ---
        
        # 1. Validar que el usuario (username) exista
        if not username:
            return {'success': False, 'message': 'El prompt no especificó un "username" para compartir.'}
        try:
            target_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return {'success': False, 'message': f'No se encontró al usuario "{username}".'}

        # 2. Validar que 'doc_id' NO sea una lista (el error de tu screenshot)
        if isinstance(doc_id, list):
            return {'success': False, 'message': 'El prompt es ambiguo ("cualquier documento"). Por favor, especifica UN solo documento.'}

        # 3. Encontrar el documento
        try:
            document = None # Iniciar como nulo
            if doc_id:
                # Esto fallará si doc_id no es un número, y será capturado
                document = Document.objects.get(id=doc_id, owner=self.user)
            elif doc_name:
                # Buscar por el nombre de archivo (usando 'icontains' para ser flexible)
                document = Document.objects.get(file__icontains=doc_name, owner=self.user)
            else:
                # Si la IA no envió ni id ni nombre
                raise Document.DoesNotExist

        except Document.DoesNotExist:
            doc_identifier = doc_id or doc_name
            if not doc_identifier:
                doc_identifier = "ninguno (el prompt fue ambiguo)"
            return {'success': False, 'message': f'No se pudo encontrar el documento "{doc_identifier}" o no te pertenece.'}
        
        except Document.MultipleObjectsReturned:
            return {'success': False, 'message': f'Múltiples documentos coinciden con "{doc_name}". Por favor, sé más específico.'}
        
        except Exception as e:
            # Capturar otros errores como el "Field 'id' expected a number..."
            return {'success': False, 'message': f'Error al buscar el documento: {str(e)}'}
        # --- FIN DE LA CORRECIÓN ---

        # 4. Ejecutar el permiso
        perm, created = DocumentPermission.objects.update_or_create(
            document=document,
            user=target_user,
            defaults={'permission_level': permission}
        )
        
        return {
            'success': True,
            'message': f'Documento "{os.path.basename(document.file.name)}" compartido con {username} con permisos de {permission}'
        }

    def _rename_tag(self, params):
        """Renombra (edita) una etiqueta existente"""
        old_name = params.get('old_tag_name')
        new_name = params.get('new_tag_name')

        if not old_name or not new_name:
            return {'success': False, 'message': 'La IA no proporcionó el nombre antiguo o el nuevo nombre de la etiqueta'}
        
        try:
            # Comprobar si la nueva etiqueta ya existe
            if Tag.objects.filter(name=new_name, owner=self.user).exists():
                return {'success': False, 'message': f'La etiqueta "{new_name}" ya existe. No se puede renombrar.'}
            
            # Encontrar y renombrar la etiqueta antigua
            tag = Tag.objects.get(name=old_name, owner=self.user)
            tag.name = new_name
            tag.save()
            
            return {
                'success': True,
                'message': f'Etiqueta "{old_name}" renombrada a "{new_name}"'
            }
        except Tag.DoesNotExist:
            return {'success': False, 'message': f'No se encontró la etiqueta "{old_name}" para renombrar.'}
        except Exception as e:
            return {'success': False, 'message': f'Error al renombrar etiqueta: {str(e)}'}

    def _delete_tag(self, params):
        """Elimina una etiqueta existente"""
        tag_name = params.get('tag_name')
        
        if not tag_name:
            return {'success': False, 'message': 'La IA no proporcionó el nombre de la etiqueta a eliminar'}
        
        try:
            # Encontrar y eliminar la etiqueta
            tag = Tag.objects.get(name=tag_name, owner=self.user)
            tag_name_deleted = tag.name # Guardar el nombre para el mensaje
            tag.delete()
            
            return {
                'success': True,
                'message': f'Etiqueta "{tag_name_deleted}" eliminada exitosamente'
            }
        except Tag.DoesNotExist:
            return {'success': False, 'message': f'No se encontró la etiqueta "{tag_name}".'}
        except Exception as e:
            return {'success': False, 'message': f'Error al eliminar etiqueta: {str(e)}'}

    def _delete_document(self, params):
        """Elimina un documento específico"""
        doc_id = params.get('document_id')
        doc_name = params.get('document_name')
        
        try:
            document = None
            if doc_id:
                document = Document.objects.get(id=doc_id, owner=self.user)
            elif doc_name:
                # Buscar por nombre de archivo
                documents = Document.objects.filter(owner=self.user)
                for doc in documents:
                    if doc_name.lower() in doc.file.name.lower():
                        document = doc
                        break
                
                if not document:
                    return {'success': False, 'message': f'No se encontró el documento "{doc_name}"'}
            else:
                return {'success': False, 'message': 'Se requiere document_id o document_name'}
            
            filename = os.path.basename(document.file.name)
            document.delete()
            
            return {
                'success': True,
                'message': f'Documento "{filename}" eliminado exitosamente'
            }
        except Document.DoesNotExist:
            return {'success': False, 'message': f'No se encontró el documento o no tienes permisos'}
        except Exception as e:
            return {'success': False, 'message': f'Error al eliminar documento: {str(e)}'}

    def _delete_all_documents(self, params):
        """Elimina todos los documentos del usuario uno por uno"""
        documents = Document.objects.filter(owner=self.user)
        total_count = documents.count()
        
        if total_count == 0:
            return {
                'success': True,
                'message': 'No tienes documentos para eliminar'
            }
        
        deleted_count = 0
        failed_files = []
        
        for doc in documents:
            try:
                filename = os.path.basename(doc.file.name)
                doc.delete()
                deleted_count += 1
            except Exception as e:
                failed_files.append(f"{filename}: {str(e)}")
        
        if failed_files:
            return {
                'success': True,
                'message': f'{deleted_count} de {total_count} documentos eliminados. Fallos: {", ".join(failed_files)}'
            }
        
        return {
            'success': True,
            'message': f'✅ Todos los documentos ({deleted_count}) han sido eliminados exitosamente'
        }

    def _delete_all_tags(self, params):
        """Elimina todas las etiquetas del usuario una por una"""
        tags = Tag.objects.filter(owner=self.user)
        total_count = tags.count()
        
        if total_count == 0:
            return {
                'success': True,
                'message': 'No tienes etiquetas para eliminar'
            }
        
        deleted_count = 0
        failed_tags = []
        
        for tag in tags:
            try:
                tag_name = tag.name
                tag.delete()
                deleted_count += 1
            except Exception as e:
                failed_tags.append(f"{tag_name}: {str(e)}")
        
        if failed_tags:
            return {
                'success': True,
                'message': f'{deleted_count} de {total_count} etiquetas eliminadas. Fallos: {", ".join(failed_tags)}'
            }
        
        return {
            'success': True,
            'message': f'✅ Todas las etiquetas ({deleted_count}) han sido eliminadas exitosamente'
        }        