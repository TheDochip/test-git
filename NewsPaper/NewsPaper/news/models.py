from django.db import models
from django.contrib.auth.models import User

class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    def __str__(self):
        return self.user.username

    def update_rating(self):
        posts_rating = self.post_set.aggregate(total=models.Sum('rating'))['total']
        if posts_rating is None:
            posts_rating = 0
        posts_rating *= 3

        comments_rating = self.user.comment_set.aggregate(total=models.Sum('rating'))['total']
        if comments_rating is None:
            comments_rating = 0

        comments_to_posts_rating = Comment.objects.filter(post__author=self).aggregate(total=models.Sum('rating'))['total']
        if comments_to_posts_rating is None:
            comments_to_posts_rating = 0

        self.rating = posts_rating + comments_rating + comments_to_posts_rating
        self.save()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class Post(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    post_type = models.CharField(max_length=10, choices = [('article', 'Статья'), ('news', 'Новости')], default='article')
    created_at = models.DateTimeField(auto_now_add=True)
    categories = models.ManyToManyField(Category, through='PostCategory')
    title = models.CharField(max_length=100)
    text = models.TextField()
    rating = models.IntegerField(default=0)

    def like(self):
        self.rating += 1
        self.save()

    def dislike(self):
        self.rating -= 1
        self.save()

    def preview(self):
        if len(self.text) > 124:
            return self.text[:124] + '...'
        return self.text

class PostCategory(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=0)

    def like(self):
        self.rating += 1
        self.save()

    def dislike(self):
        self.rating -= 1
        self.save()