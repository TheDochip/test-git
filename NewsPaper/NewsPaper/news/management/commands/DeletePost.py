from django.core.management import BaseCommand, CommandError
from news.models import Post, Category

class Command(BaseCommand):
    help = 'Удаления статей из выбранной категории'

    def add_arguments(self, parser):
        parser.add_argument('category', type=str)

    def handle(self, *args, **options):
        answer = input(f'вы правда хотите удалить все статьи в категории {options["category"]}? yes/no')
        if answer != 'yes':
            self.stdout.write(self.style.ERROR('Отменено'))
            return
        try:
            category = Category.objects.get(name=options['category'])
            Post.objects.filter(category=category).delete()

            self.stdout.write(self.style.SUCCESS(f'Successfully deleted all news from category {category.name}'))
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Could not fild category {options["category"]}'))
