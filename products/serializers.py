from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo de Categorías.
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo de Productos.
    """
    # Para mostrar el nombre de la categoría en lugar de solo su ID.
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.SlugField(source='category.slug', read_only=True)
    image = serializers.ImageField(required=False, allow_null=True) # Make image writable

    class Meta:
        model = Product
        # Incluimos todos los campos del modelo y el campo extra 'category_name'.
        fields = [
            'id',
            'category',
            'category_name',
            'category_slug',
            'name',
            'description',
            'price',
            'stock',
            'image',
            'created_at',
            'updated_at'
        ]
        # Hacemos que 'category' sea de solo escritura, ya que mostramos 'category_name' para leer.
        extra_kwargs = {
            'category': {'write_only': True}
        }

    def to_representation(self, instance):
        """
        Construye la URL completa de la imagen al serializar.
        """
        representation = super().to_representation(instance)
        if instance.image:
            request = self.context.get('request')
            if request:
                representation['image'] = request.build_absolute_uri(instance.image.url)
            else:
                representation['image'] = instance.image.url
        return representation