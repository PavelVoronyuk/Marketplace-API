from flask import Blueprint
from flask_restx import Resource, Namespace, fields, inputs
from flask_restx.reqparse import RequestParser
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Product, Users

products = Blueprint("product", __name__)

ns_products = Namespace("products", description="Namespace for products")


get_delete_product_parser = RequestParser()
get_delete_product_parser.add_argument("product_id", type=int, required=True, location="args")

post_product_parser = RequestParser()
post_product_parser.add_argument("product_name", type=str, required=True, location="args")
post_product_parser.add_argument("product_desc", type=str, required=True, location="args")
post_product_parser.add_argument("product_price", type=int, required=True, location="args")
post_product_parser.add_argument("is_available", type=bool, required=True, location="args", choices=(True, False))

put_product_parser = RequestParser()
put_product_parser.add_argument("product_id", type=int, required=True, location="args")
put_product_parser.add_argument("product_name", type=str, required=True, location="args")
put_product_parser.add_argument("product_desc", type=str, required=True, location="args")
put_product_parser.add_argument("product_price", type=int, required=True, location="args")
put_product_parser.add_argument("is_available", type=inputs.boolean, required=True, location="args", choices=(True, False))

patch_product_parser = RequestParser()
patch_product_parser.add_argument("product_id", type=int, required=True, location="args")
patch_product_parser.add_argument("product_name", type=str, required=False, location="args")
patch_product_parser.add_argument("product_desc", type=str, required=False, location="args")
patch_product_parser.add_argument("product_price", type=int, required=False, location="args")
patch_product_parser.add_argument("is_available", type=inputs.boolean, required=False, location="args", choices=(True, False))

get_search = RequestParser()
get_search.add_argument("price_min", type=int, default=1 ,required=False, location="args")
get_search.add_argument("price_max", type=int, default=10000000, required=False, location="args")
get_search.add_argument("keyword", type=str, required=True, location="args")


get_product_model = ns_products.model("Product", {
    "id": fields.Integer(attribute="ProductId"),
    "product_name": fields.String(attribute="ProductName"),
    "product_desc": fields.String(attribute="ProductDescription"),
    "product_price": fields.Integer(attribute="ProductPrice"),
    "product_owner": fields.String(attribute="Owner.Username"),
    "is_available": fields.Boolean(attribute="IsAvailable"),
})

get_product_model = ns_products.model("Product", {
    "product_name": fields.String(attribute="ProductName"),
    "product_desc": fields.String(attribute="ProductDescription"),
    "product_price": fields.Integer(attribute="ProductPrice"),
    "product_owner": fields.String(attribute="Owner.Username"),
    "is_available": fields.Boolean(attribute="IsAvailable"),
})

@ns_products.route("/")
class ProductsView(Resource):
    @ns_products.marshal_with(get_product_model)
    @ns_products.expect(get_delete_product_parser, validate=True)
    def get(self):
        args = get_delete_product_parser.parse_args()

        product: Product = Product.select(Product, Users).join(Users).where(Product.ProductId == args["product_id"]).get_or_none()


        return product

    @ns_products.expect(post_product_parser)
    @jwt_required()
    def post(self):
        args = post_product_parser.parse_args()

        try:
            user: Users
            user = Users.get_or_none(Users.Email==get_jwt_identity())
            Product.create(ProductName=args["product_name"],
                            ProductDescription=args["product_desc"],
                            ProductPrice=args["product_price"],
                            Owner=user.UserId,
                            IsAvailable=args["is_available"])
            return "Success", 200
        except Exception as e:
            return str(e), 400

    @ns_products.expect(put_product_parser)
    @jwt_required()
    def put(self):
        args = put_product_parser.parse_args()

        try:
            user: Users
            product: Product
            product = Product.get_or_none(Product.ProductId == args["product_id"])
            user = Users.get_or_none(Users.Email==get_jwt_identity())
            if product and product.Owner == user or user.Role.lower() == "admin":
                Product.update(ProductName=args["product_name"],
                                                ProductDescription=args["product_desc"],
                                                ProductPrice=args["product_price"],
                                                IsAvailable=args["is_available"]).where(Product.ProductId == args["product_id"]).execute()
                return "Success", 200
            else:
                return "You are not the owner or product does not exist!", 400
        except Exception as e:
            return str(e), 400

    @ns_products.expect(patch_product_parser)
    @jwt_required()
    def patch(self):
        args = patch_product_parser.parse_args()
        field_mapping = {
            "product_name": "ProductName",
            "product_desc": "ProductDescription",
            "product_price": "ProductPrice",
            "is_available": "IsAvailable",
        }
        try:
            user: Users
            product: Product
            product = Product.get_or_none(Product.ProductId == args["product_id"])
            user = Users.get_or_none(Users.Email==get_jwt_identity())
            if product and product.Owner == user or user.Role.lower() == "admin":
                updated_fields = {field_mapping[key]: value for key, value in args.items() if value is not None and key in field_mapping}
                for key, value in updated_fields.items():
                    setattr(product, key, value)

                product.save()
                return "Success", 200
            else:
                return "You are not the owner or product does not exist!", 400

        except Exception as e:
            return str(e), 400

    @ns_products.expect(get_delete_product_parser)
    @jwt_required()
    def delete(self):
        product_id = get_delete_product_parser.parse_args()["product_id"]

        try:
            user: Users
            product: Product
            product = Product.get_or_none(Product.ProductId == product_id)
            user = Users.get_or_none(Users.Email==get_jwt_identity())
            if product and product.Owner == user or user.Role.lower() == "admin":
                product.delete_instance()
                return "Success", 200
            else:
                return "You are not the owner or product does not exist!", 400
        except Exception as e:
            return str(e), 400

@ns_products.route("/search")
class Search(Resource):
    @ns_products.expect(get_search)
    def get(self):
        args = get_search.parse_args()
        price_min = args["price_min"]
        price_max = args["price_max"]
        keyword = args["keyword"]

        try:
            if price_max > price_min and price_max > 0 and price_min > 0:
                products = Product.select().where((Product.ProductPrice.between(price_min, price_max)) &
                                                ((Product.ProductName.ilike(f"%{keyword}%")) |
                                                (Product.ProductDescription.ilike(f"%{keyword}%"))) &
                                                Product.IsAvailable == True)
                products_list = [product.__data__ for product in products]
            else:
                return "Wrong price", 400

            if products_list:
                return products_list, 200
            else:
                return "No products found", 200
        except Exception as e:
            return str(e), 400
