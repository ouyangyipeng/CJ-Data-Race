// case45: Channel多通道测试
// 测试多个Channel的使用（无竞争）

main() {
    let ch1 = Channel<Int64>(10)
    let ch2 = Channel<Int64>(10)
    var result: Int64 = 0
    
    spawn {
        ch1.send(1)
        ch2.send(2)
    }
    
    spawn {
        let v1 = ch1.receive()
        let v2 = ch2.receive()
        result = v1 + v2
    }
}