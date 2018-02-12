#!/bin/sh

curl 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.json' | \
jq '
[
	.terms.OnDemand as $terms
	| .products
	| .[]
	| select(.productFamily == "Compute Instance")
	| select($terms[.sku])
	| (
		. +
		{ cost: [
			$terms[.sku]
			| .[]][0]
			| [.priceDimensions | .[]][0]
			| .pricePerUnit.USD |
			tonumber
		}
	)
]' > in/ondemandcosts.json
