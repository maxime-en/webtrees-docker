ARG PHP_VERSION=8.3.22-apache-bookworm
ARG WEBTREES_VERSION=2.2.1
ARG PATCH_VERSION=2

FROM php:$PHP_VERSION

# https://hub.docker.com/_/php
# https://github.com/NathanVaughn/webtrees-docker/issues/160
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"

ENV WEBTREES_HOME="/var/www/webtrees"
WORKDIR $WEBTREES_HOME
RUN groupadd -g 16847 webtrees && useradd -m -u 16847 -g webtrees webtrees

# install pre-reqs
# mariadb-client provides mysqladmin
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y \
    curl \
    libmagickwand-dev \
    libpq-dev \
    libzip-dev \
    mariadb-client \
    patch \
    python3 \
    unzip \
    --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

RUN pecl install imagick \
 && docker-php-ext-enable imagick \
 && docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install -j"$(nproc)" pdo pdo_mysql pdo_pgsql zip intl gd exif

# remove old apt stuff
RUN apt-get purge gcc g++ make -y \
 && apt-get autoremove --purge -y \
 && apt-get clean \
 && rm -rf /var/tmp/* /etc/apache2/sites-enabled/000-*.conf

ARG WEBTREES_VERSION
COPY webtrees-${WEBTREES_VERSION}.zip webtrees.zip
RUN unzip -q webtrees.zip -d /var/www/ && rm webtrees.zip && rm $WEBTREES_HOME/*.md

# Disable version update prompt. Webtrees should not be upgrading itself,
# users should be using tagged container versions
ARG PATCH_VERSION
COPY patches/UpgradeService${PATCH_VERSION}.patch /UpgradeService.patch
RUN patch app/Services/UpgradeService.php /UpgradeService.patch \
 && rm /UpgradeService.patch \
# Delete file that caused email issues
# https://www.webtrees.net/index.php/fr/forum/help-for-2-0/36616-email-error-after-update-to-2-0-21#89985
# https://github.com/NathanVaughn/webtrees-docker/issues/88
 && rm vendor/egulias/email-validator/src/Validation/MessageIDValidation.php

# enable apache modules
RUN a2enmod rewrite && rm -rf /var/www/html

# copy apache/php configs
COPY .htaccess ./
COPY apache/webtrees.conf /etc/apache2/sites-enabled/webtrees.conf
COPY apache/ports.conf /etc/apache2/ports.conf
RUN chown -R webtrees:webtrees /usr/local/etc/php

# entrypoint
COPY docker-entrypoint.py /

# healthcheck
COPY docker-healthcheck.sh /
RUN chmod +x /docker-healthcheck.sh

# final Docker config
USER webtrees
EXPOSE 8080
VOLUME ["$WEBTREES_HOME/data"]

HEALTHCHECK CMD /docker-healthcheck.sh
ENTRYPOINT ["python3", "/docker-entrypoint.py"]
