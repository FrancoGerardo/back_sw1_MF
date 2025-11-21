from django.test import TestCase, Client
from django.urls import reverse
import json

# Create your tests here.


class ApiEndpointTests(TestCase):

    def setUp(self):
        # setUp se ejecuta antes de cada prueba. Aquí creamos un cliente de prueba.
        self.client = Client()

    def test_test_endpoint_success(self):
        # Obtenemos la URL del endpoint usando su nombre 'test_endpoint'
        url = reverse('test_endpoint')
        # Hacemos una petición GET a esa URL
        response = self.client.get(url)

        # Verificamos que la respuesta sea exitosa (código 200)
        self.assertEqual(response.status_code, 200)
        # Verificamos que el contenido de la respuesta sea el esperado
        expected_data = {
            'message': '¡Hola desde el backend de Django!', 'status': 'ok'}
        self.assertJSONEqual(
            str(response.content, encoding='utf8'), expected_data)
