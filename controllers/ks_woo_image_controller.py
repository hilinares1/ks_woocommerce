import base64
import logging
import werkzeug.wrappers
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class KsWooImageHandler(http.Controller):
    @http.route(['/ks_woo_image/<string:db>/<int:uid>/<int:product_template_id>/<int:product_image_id>/<string:image>'],
                auth='none',
                csrf=False, methods=['GET', 'POST'], type='http')
    def create_woo_public_image_url(self, db=False, uid=False, product_template_id=False, product_image_id=False,
                                    image=False, **post):
        """
        Creating a Public URL for the Woocommerce Image Product

        :param product_template_id: Product Data
        :param product_image_id: Product Image Data
        :param image: Main Image Data
        :param post:
        :return: Response Data
        """
        db = db.strip()
        request.session.db = db
        request.session.uid = uid
        request.uid = uid
        response = werkzeug.wrappers.Response()
        if product_image_id and product_template_id and image:
            product_template = request.env['product.template'].sudo().search([('id', '=', product_template_id)])
            if product_template.ks_product_image_ids:
                product_image_record = product_template.ks_product_image_ids.search([('id', '=', product_image_id)])
                if product_image_record.ks_image:
                    decode_image = base64.urlsafe_b64decode(product_image_record.ks_image)
                    image_id = base64.b64decode(product_image_record.ks_image)
                    status, response_headers, content = request.env['ir.http'].sudo().binary_content(
                        model='ks.woo.product.image', id=product_image_record.id,
                        field='ks_image')
                    response.data = decode_image
                    image_content_base64 = base64.b64decode(content) if content else ''
                    response_headers.append(('Content-Length', len(image_content_base64)))
                    return request.make_response(image_content_base64, response_headers)
                    # decode_image = base64.b64decode(product_image_record.ks_image)
                    # response.data = decode_image
                    # response.mimetype = self._ks_find_mimetype(product_image_record.ks_file_name, decode_image)

                else:
                    _logger.warning('[WooCommerce] Product image not found on this URL')
            else:
                _logger.warning('[WooCommerce] Product image not found on this URL')
        return response

    @http.route(
        ['/ks_woo_image/variant/<string:db>/<int:uid>/<int:product_product_id>/<int:product_image_id>/<string:image>'],
        auth='none',
        csrf=False, methods=['GET', 'POST'], type='http')
    def create_woo_public_product_variant_image_url(self, db=False, uid=False, product_product_id=False,
                                                    product_image_id=False, image=False, **post):
        db = db.strip()
        request.session.db = db
        request.session.uid = uid
        request.uid = uid
        response = werkzeug.wrappers.Response()
        if product_image_id and product_product_id and image:
            product_product = request.env['product.product'].sudo().search([('id', '=', product_product_id)])
            if product_product.ks_product_image_id:
                product_image_record = product_product.ks_product_image_id
                if product_image_record.ks_image:
                    decode_image = base64.urlsafe_b64decode(product_image_record.ks_image)
                    image_id = base64.b64decode(product_image_record.ks_image)
                    status, response_headers, content = request.env['ir.http'].sudo().binary_content(
                        model='ks.woo.product.variant.image', id=product_image_record.id,
                        field='ks_image')
                    response.data = decode_image
                    image_content_base64 = base64.b64decode(content) if content else ''
                    response_headers.append(('Content-Length', len(image_content_base64)))
                    return request.make_response(image_content_base64, response_headers)
                    # decode_image = base64.b64decode(product_image_record.ks_image)
                    # response.data = decode_image
                    # response.mimetype = self._ks_find_mimetype(product_image_record.ks_file_name, decode_image)
                else:
                    _logger.warning('[WooCommerce] Product image not found on this URL')
            else:
                _logger.warning('[WooCommerce] Product image not found on this URL')
        return response

    # def _ks_find_mimetype(self, filename, decode_image):
    #     mime_type = mimetypes.guess_type(filename)
    #     image_mimetype = mime_type[0]
    #     if not image_mimetype:
    #         if decode_image:
    #             image_mimetype = magic.from_buffer(decode_image, mime=True)
    #         else:
    #             image_mimetype = 'image/png'
    #     return image_mimetype
