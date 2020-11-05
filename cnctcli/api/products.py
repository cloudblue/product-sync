# -*- coding: utf-8 -*-

# This file is part of the Ingram Micro Cloud Blue Connect connect-cli.
# Copyright (c) 2019-2020 Ingram Micro. All Rights Reserved.

from cnctcli.api.utils import (
    handle_http_error,
)

from cnct import ClientError
from cnct.rql import R


def create_unit(client, data):
    try:
        res = (
            client.ns('settings')
            .collection('units')
            .create(data)
        )
    except ClientError as error:
        handle_http_error(error)
    return res


def get_item(client, product_id, item_id):
    try:
        res = (
            client.collection('products')
            [product_id]
            .collection('items')
            [item_id]
            .get()
        )
    except ClientError as error:
        if error.status_code == 404:
            return
        handle_http_error(error)
    return res


def get_item_by_mpn(client, product_id, mpn):
    rql = R().mpn.eq(mpn)

    try:
        res = (
            client.collection('products')
            [product_id]
            .collection('items')
            .filter(rql)
        )

    except ClientError as error:
        if error.status_code == 404:
            return
        handle_http_error(error)

    return res.first()


def create_item(client, product_id, data):
    try:
        res = (
            client.collection('products')
            [product_id]
            .collection('items')
            .create(data)
        )
    except ClientError as error:
        handle_http_error(error)

    return res


def update_item(client, product_id, item_id, data):
    try:
        res = (
            client.collection('products')
            [product_id]
            .collection('items')
            [item_id]
            .update(data)
        )
    except ClientError as error:
        handle_http_error(error)

    return res


def delete_item(client, product_id, item_id):
    try:
        (
            client.collection('products')
            [product_id]
            .collection('items')
            .delete(item_id)
        )
    except ClientError as error:
        if error.status_code != 204:
            handle_http_error(error)
