FROM alpine:3.19
RUN apk add --no-cache curl jq bash
COPY auto-withdraw.sh /auto-withdraw.sh
RUN chmod +x /auto-withdraw.sh
CMD ["/auto-withdraw.sh"]
