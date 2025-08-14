from django.conf import settings
from django.utils.translation import get_language

def global_context(request):
	return {
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}