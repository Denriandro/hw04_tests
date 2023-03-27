from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Post, User, Group

User = get_user_model()


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            description='Описание тестовой группы',
            slug='test_slug',
            title='Тестовая группа',
        )

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_post_edit_form(self):
        """При отправке формы со страницы post_edit происходит изменение
        поста с post_id в БД."""
        post = Post.objects.create(
            author=self.author,
            group=self.group,
            text='Текст поста для редактирования.',
        )

        edited_group = Group.objects.create(
            description='Описание тестовой группы для редактирования поста',
            slug='test_edit_slug',
            title='Тестовая группа для редактирования поста',
        )

        form_data = {
            'group': edited_group.id,
            'text': 'Отредактированный текст поста.'
        }

        self.author_client.post(
            reverse('posts:post_edit', args=[post.id]),
            data=form_data,
            follow=True
        )

        edited_post = Post.objects.get(id=post.id)

        self.assertEqual(post.author, edited_post.author)
        self.assertEqual(form_data['group'], edited_post.group.id)
        self.assertEqual(form_data['text'], edited_post.text)

    def test_post_create_form(self):
        """При отправке формы со страницы create_post создается новая запись в
        БД."""
        post_count = Post.objects.count()
        group = Group.objects.create(
            description='Описание тестовой группы для создания поста',
            slug='test_create_slug',
            title='Тестовая группа для создания поста',
        )
        form_data = {
            'group': group.id,
            'text': 'Тестовый текст поста',
        }
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse(
                'posts:profile', kwargs={'username': self.author}
        ))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                group=group.id,
                text='Тестовый текст поста',
            ).exists()
        )
