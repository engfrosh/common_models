# Generated by Django 4.1 on 2022-12-21 20:07

import common_models.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BooleanSetting',
            fields=[
                ('id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('value', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Boolean Setting',
                'verbose_name_plural': 'Boolean Settings',
            },
        ),
        migrations.CreateModel(
            name='ChannelTag',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, unique=True, verbose_name='Tag Name')),
            ],
            options={
                'verbose_name': 'Channel Tag',
                'verbose_name_plural': 'Channel Tags',
            },
        ),
        migrations.CreateModel(
            name='DiscordBingoCards',
            fields=[
                ('discord_id', models.PositiveBigIntegerField(db_index=True, unique=True)),
                ('bingo_card', models.PositiveIntegerField(primary_key=True, serialize=False)),
            ],
            options={
                'verbose_name': 'Discord Bingo Card',
                'verbose_name_plural': 'Discord Bingo Cards',
            },
        ),
        migrations.CreateModel(
            name='DiscordGuild',
            fields=[
                ('id', models.PositiveBigIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('deleted', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Discord Guild',
                'verbose_name_plural': 'Discord Guilds',
                'permissions': [],
            },
        ),
        migrations.CreateModel(
            name='DiscordOverwrite',
            fields=[
                ('descriptive_name', models.CharField(blank=True, default='', max_length=100)),
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='Overwrite ID')),
                ('user_id', models.PositiveBigIntegerField(verbose_name='User or Role ID')),
                ('type', models.IntegerField(choices=[(0, 'Role'), (1, 'Member')])),
                ('allow', models.PositiveBigIntegerField(verbose_name='Allowed Overwrites')),
                ('deny', models.PositiveBigIntegerField(verbose_name='Denied Overwrites')),
            ],
            options={
                'verbose_name': 'Discord Permission Overwrite',
                'verbose_name_plural': 'Discord Permission Overwrites',
            },
        ),
        migrations.CreateModel(
            name='FroshRole',
            fields=[
                ('name', models.CharField(max_length=64, unique=True, verbose_name='Role Name')),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='auth.group')),
            ],
            options={
                'verbose_name': 'Frosh Role',
                'verbose_name_plural': 'Frosh Roles',
            },
        ),
        migrations.CreateModel(
            name='Puzzle',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=200, unique=True)),
                ('answer', models.CharField(max_length=100)),
                ('require_photo_upload', models.BooleanField(default=True)),
                ('secret_id', models.SlugField(default=common_models.models.random_puzzle_secret_id, max_length=64, unique=True)),
                ('enabled', models.BooleanField(default=True)),
                ('order', models.DecimalField(decimal_places=3, max_digits=8)),
                ('qr_code', models.ImageField(blank=True, upload_to=common_models.models.scavenger_qr_code_path)),
                ('puzzle_text', models.CharField(blank=True, max_length=2000, verbose_name='Text')),
                ('puzzle_file', models.FileField(blank=True, upload_to=common_models.models.puzzle_path)),
                ('puzzle_file_display_filename', models.CharField(blank=True, max_length=256)),
                ('puzzle_file_download', models.BooleanField(default=False)),
                ('puzzle_file_is_image', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Scavenger Puzzle',
                'verbose_name_plural': 'Scavenger Puzzles',
                'permissions': [('guess_scavenger_puzzle', 'Can guess for scavenger puzzle'), ('manage_scav', 'Can manage scav')],
            },
        ),
        migrations.CreateModel(
            name='PuzzleStream',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('enabled', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Scavenger Puzzle Stream',
                'verbose_name_plural': 'Scavenger Puzzle Streams',
            },
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('display_name', models.CharField(max_length=64, unique=True, verbose_name='Team Name')),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='auth.group')),
                ('scavenger_team', models.BooleanField(default=True)),
                ('scavenger_finished', models.BooleanField(default=False, verbose_name='Finished Scavenger')),
                ('scavenger_locked_out_until', models.DateTimeField(blank=True, default=None, null=True)),
                ('scavenger_enabled_for_team', models.BooleanField(default=True)),
                ('trade_up_team', models.BooleanField(default=True)),
                ('trade_up_enabled_for_team', models.BooleanField(default=True)),
                ('coin_amount', models.BigIntegerField(default=0, verbose_name='Coin Amount')),
                ('color', models.PositiveIntegerField(blank=True, default=None, null=True, verbose_name='Hex Color Code')),
            ],
            options={
                'verbose_name': 'Team',
                'verbose_name_plural': 'Teams',
                'permissions': [('change_team_coin', 'Can change the coin amount of a team.'), ('view_team_coin_standings', 'Can view the coin standings of all teams.')],
            },
        ),
        migrations.CreateModel(
            name='UniversityProgram',
            fields=[
                ('name', models.CharField(max_length=64, unique=True, verbose_name='Program Name')),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='auth.group')),
            ],
            options={
                'verbose_name': 'Program',
                'verbose_name_plural': 'Programs',
            },
        ),
        migrations.CreateModel(
            name='UserDetails',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('name', models.CharField(max_length=64, verbose_name='Name')),
                ('pronouns', models.CharField(blank=True, max_length=20, verbose_name='Pronouns')),
                ('invite_email_sent', models.BooleanField(default=False, verbose_name='Invite Email Sent')),
            ],
            options={
                'verbose_name': 'User Details',
                'verbose_name_plural': "Users' Details",
            },
        ),
        migrations.CreateModel(
            name='VerificationPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(auto_now=True)),
                ('photo', models.ImageField(upload_to=common_models.models._puzzle_verification_photo_upload_path)),
                ('approved', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='VirtualTeam',
            fields=[
                ('role_id', models.PositiveBigIntegerField(primary_key=True, serialize=False)),
                ('num_members', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Virtual Team',
                'verbose_name_plural': 'Virtual Teams',
            },
        ),
        migrations.CreateModel(
            name='TeamTradeUpActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entered_at', models.DateTimeField(auto_now=True)),
                ('object_name', models.CharField(blank=True, max_length=200, null=True)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common_models.team')),
                ('verification_photo', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='common_models.verificationphoto')),
            ],
            options={
                'verbose_name': 'Team Trade Up Activity',
                'verbose_name_plural': 'Team Trade Up Activities',
            },
        ),
        migrations.CreateModel(
            name='TeamPuzzleActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puzzle_start_at', models.DateTimeField(auto_now=True)),
                ('puzzle_completed_at', models.DateTimeField(blank=True, default=None, null=True)),
                ('locked_out_until', models.DateTimeField(blank=True, default=None, null=True)),
                ('puzzle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common_models.puzzle')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common_models.team')),
                ('verification_photo', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='common_models.verificationphoto')),
            ],
            options={
                'verbose_name': 'Team Puzzle Activity',
                'verbose_name_plural': 'Team Puzzle Activities',
                'unique_together': {('team', 'puzzle')},
            },
        ),
        migrations.AddField(
            model_name='team',
            name='puzzles',
            field=models.ManyToManyField(through='common_models.TeamPuzzleActivity', to='common_models.puzzle'),
        ),
        migrations.CreateModel(
            name='PuzzleGuess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(auto_now=True)),
                ('value', models.CharField(max_length=100)),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='common_models.teampuzzleactivity')),
            ],
            options={
                'verbose_name': 'Puzzle Guess',
                'verbose_name_plural': 'Puzzle Guesses',
            },
        ),
        migrations.AddField(
            model_name='puzzle',
            name='stream',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='common_models.puzzlestream'),
        ),
        migrations.CreateModel(
            name='MagicLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(default=common_models.models.random_token, max_length=64)),
                ('expiry', models.DateTimeField(default=common_models.models.days5)),
                ('delete_immediately', models.BooleanField(default=True)),
                ('qr_code', models.ImageField(blank=True, upload_to=common_models.models.magic_link_qr_code_path)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DiscordUser',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='Discord ID')),
                ('discord_username', models.CharField(blank=True, max_length=100)),
                ('discriminator', models.IntegerField(blank=True)),
                ('access_token', models.CharField(blank=True, max_length=40)),
                ('expiry', models.DateTimeField(blank=True, null=True)),
                ('refresh_token', models.CharField(blank=True, max_length=40)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Discord User',
                'verbose_name_plural': 'Discord Users',
            },
        ),
        migrations.CreateModel(
            name='DiscordRole',
            fields=[
                ('role_id', models.PositiveBigIntegerField(primary_key=True, serialize=False, verbose_name='Discord Role ID')),
                ('group_id', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auth.group')),
            ],
            options={
                'verbose_name': 'Discord Role',
                'verbose_name_plural': 'Discord Roles',
            },
        ),
        migrations.CreateModel(
            name='DiscordChannel',
            fields=[
                ('id', models.PositiveBigIntegerField(primary_key=True, serialize=False, verbose_name='Discord Channel ID')),
                ('name', models.CharField(blank=True, default='', max_length=100, verbose_name='Discord Channel Name')),
                ('type', models.IntegerField(choices=[(0, 'GUILD_TEXT'), (1, 'DM'), (2, 'GUILD_VOICE'), (3, 'GROUP_DM'), (4, 'GUILD_CATEGORY'), (5, 'GUILD_NEWS'), (6, 'GUILD_STORE'), (10, 'GUILD_NEWS_THREAD'), (11, 'GUILD_PUBLIC_THREAD'), (12, 'GUILD_PRIVATE_THREAD'), (13, 'GUILD_STAGE_VOICE')], verbose_name='Channel Type')),
                ('locked_overwrites', models.ManyToManyField(blank=True, to='common_models.discordoverwrite')),
                ('tags', models.ManyToManyField(blank=True, to='common_models.channeltag')),
                ('unlocked_overwrites', models.ManyToManyField(blank=True, related_name='unlocked_channel_overwrites', to='common_models.discordoverwrite')),
            ],
            options={
                'verbose_name': 'Discord Channel',
                'verbose_name_plural': 'Discord Channels',
                'permissions': [('lock_channels', 'Can lock or unlock discord channels.')],
            },
        ),
        migrations.AlterUniqueTogether(
            name='puzzle',
            unique_together={('order', 'stream')},
        ),
    ]
