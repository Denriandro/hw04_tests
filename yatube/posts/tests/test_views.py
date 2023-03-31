import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms
from django.test import TestCase, override_settings
from django.urls import reverse
from posts.models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст тестового поста.',
            group=cls.group,
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif',
        )

    def setUp(self):
        self.client.force_login(self.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
                'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Список постов страницы index."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_group_list_show_correct_context(self):
        """Список постов отфильтрованных по группе."""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['page_obj'][0], self.post)
        self.assertEqual(response.context['group'], self.group)

    def test_profile_show_correct_context(self):
        """Список постов отфильтрованных по пользователю."""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user}))
        self.assertEqual(response.context['page_obj'][0], self.post)
        self.assertEqual(response.context['author'], self.user)

    def test_post_detail_show_correct_context(self):
        """Один пост, отфильтрованный по id."""
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context['one_post'], self.post)

    def test_post_create_and_edit_show_correct_context(self):
        """Форма создания/редактирования поста, отфильтрованного по id."""
        views = [
            self.client.get(reverse('posts:post_create')),
            self.client.get(
                reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        ]
        for response in views:
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.models.ModelChoiceField
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context['form'].fields[value]
                    self.assertIsInstance(form_field, expected)

    def test_post_in_group(self):
        """Проверяем наличие group при создании поста на главной, групп,
        профиля страницах."""

        urls = [
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user}/',
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                posts = response.context['page_obj']
                self.assertIn(self.post, posts)

    def test_post_with_group_not_into_another_group(self):
        """Проверяем не попал ли пост в непредназначенную группу."""
        group = Group.objects.create(
            title='Другая тестовая группа',
            slug='another_slug',
            description='Другое тестовое описание',
        )
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': 'another_slug'}))
        posts = response.context['page_obj']
        expected = Post.objects.filter(group=group)
        self.assertNotIn(expected, posts)

    def test_image_in_context_of_response_index(self):
        """Проверяем, что при выводе поста с картинкой изображение передаётся
        в context на главную, групп, профиля, поста страниц."""
        views = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user}),
        )
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст поста c картинкой',
            'image': self.uploaded,
            'author': self.user,
        }
        self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        for view in views:
            with self.subTest(view=view):
                new_post = Post.objects.latest('id').image.name
                response = self.client.get(view)
                first_object = response.context['page_obj'][0]
                post_image = first_object.image.name
                self.assertEqual(post_image, new_post)

    def test_image_post_detail(self):
        """Проверяем, что при выводе поста с картинкой изображение передаётся
        в context на страницу одного поста."""
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст поста c картинкой',
            'image': self.uploaded,
            'author': self.user,
        }
        self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        first_object = response.context['one_post']
        self.assertIsNotNone(first_object.image)


class PaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test-user-0')
        cls.group = Group.objects.create(
            title='Test-group', slug='test-slug',
            description='test-description'
        )
        Post.objects.bulk_create(
            [Post(
                author=cls.author,
                group=cls.group,
                text=f'Test-text-{i}'
            ) for i in range(13)
            ])
        cls.CONST = {
            'RECORD_ON_PAGE': 10,
            'LEFT_RECORDS': 3,
        }

    def test_paginator(self):
        """Проверяем 10 записей на 1-ой странице и остаток на 2-ой"""

        def test_page_contains_ten_records(route):
            response = self.client.get(route)
            self.assertEqual(
                len(response.context['page_obj']), self.CONST['RECORD_ON_PAGE']
            )

        def test_page_contains_three_records(route):
            response = self.client.get(route + '?page=2')
            self.assertEqual(
                len(response.context['page_obj']), self.CONST['LEFT_RECORDS']
            )

        routes = {
            'index': reverse('posts:index'),
            'group_list': reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ),
            'profile': reverse(
                'posts:profile', kwargs={'username': self.author}
            ),
        }
        for route in routes:
            test_page_contains_ten_records(routes[route])
            test_page_contains_three_records(routes[route])
