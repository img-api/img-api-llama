# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

# Copyright (c) Meta Platforms, Inc. and affiliates.
# This software may be used and distributed in accordance with the terms of the Llama 3 Community License Agreement.

import asyncio

import fire
from llama_models.llama3_1.api.datatypes import Attachment, URL, UserMessage

from multi_turn import prompt_to_message, run_main


def main(host: str, port: int, disable_safety: bool = False):
    result = asyncio.run(
        run_main(
            [
                prompt_to_message("Summarize this text to be displayed in a website, format it nicely adding carriage returns and bullet points: International Business Machines Corporation, together with its subsidiaries, provides integrated solutions and services worldwide. The company operates through Software, Consulting, Infrastructure, and Financing segments. The Software segment offers a hybrid cloud and AI platforms that allows clients to realize their digital and AI transformations across the applications, data, and environments in which they operate. The Consulting segment focuses on skills integration for strategy, experience, technology, and operations by domain and industry. The Infrastructure segment provides on-premises and cloud based server, and storage solutions, as well as life-cycle services for hybrid cloud infrastructure deployment. The Financing segment offers client and commercial financing, facilitates IBM clients' acquisition of hardware, software, and services. The company has a strategic partnership to various companies including hyperscalers, service providers, global system integrators, and software and hardware vendors that includes Adobe, Amazon Web services, Microsoft, Oracle, Salesforce, Samsung Electronics and SAP, and others. The company was formerly known as Computing-Tabulating-Recording Co. International Business Machines Corporation was incorporated in 1911 and is headquartered in Armonk, New York."),
            ],
            host=host,
            port=port,
            disable_safety=disable_safety,
        )
    )

    print(str(result))

if __name__ == "__main__":
    fire.Fire(main)
